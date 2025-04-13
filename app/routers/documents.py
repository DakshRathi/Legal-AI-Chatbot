# app/routers/documents.py
from fastapi import (
    APIRouter, Depends, HTTPException, status,
    UploadFile, File, BackgroundTasks
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Local imports
from app.db.database import get_db
from app.db.models import Document, User
from app.auth.dependencies import get_current_active_user
from app.models.document import DocumentCreateResponse, DocumentRead, DocumentListResponse
from ml_core.document_processor import process_document_content
from ml_core.vector_store import add_document_to_store, delete_documents_from_store

router = APIRouter()

# Define allowed content types
ALLOWED_CONTENT_TYPES = [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document", # .docx
    "image/png",
    "image/jpeg"
]

MAX_FILE_SIZE = 10 * 1024 * 1024 # 10 MB limit

def add_to_vector_store_background(doc_id: int, user_id: int, text: str):
    """Synchronous wrapper function for background task execution."""
    print(f"Background task started: Adding doc_id {doc_id} to vector store.")
    try:
        # Call the synchronous function directly
        add_document_to_store(doc_id=doc_id, user_id=user_id, text=text)
    except Exception as e:
         import traceback
         print(f"ERROR in background task for doc_id {doc_id}: {e}")
         print(traceback.format_exc())
    finally:
        print(f"Background task finished: Adding doc_id {doc_id} to vector store.")


@router.post(
    "/upload",
    response_model=DocumentCreateResponse,
    status_code=status.HTTP_202_ACCEPTED, # Use 202 Accepted as processing happens in background
    summary="Upload a document for processing"
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Document file (PDF, DOCX, PNG, JPG/JPEG)"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Handles document upload, basic validation, initial processing (text/entity extraction),
    saving metadata to DB, and schedules vector embedding in the background.
    """
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}. Allowed types: {', '.join(ALLOWED_CONTENT_TYPES)}"
        )

    # Check file size (read content once)
    file_content = await file.read()
    if len(file_content) > MAX_FILE_SIZE:
         raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds the limit of {MAX_FILE_SIZE // (1024*1024)} MB."
        )

    print(f"Received file: {file.filename}, Size: {len(file_content)} bytes, Type: {file.content_type}")

    # Always close the file explicitly
    await file.close()

    # Process document content (CPU-bound, consider running in threadpool for heavy load)
    processed_data = process_document_content(file_content=file_content, filename=file.filename)

    if not processed_data or not processed_data.get("text"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to extract text content from the document: {file.filename}"
        )

    extracted_text = processed_data["text"]
    extracted_entities = processed_data["entities"]

    # Save document metadata to SQL database
    db_document = Document(
        filename=file.filename,
        owner_id=current_user.id,
        metadata_json=extracted_entities # Store extracted entities
    )
    db.add(db_document)
    try:
        await db.commit()
        await db.refresh(db_document)
        print(f"Saved document metadata to DB. Doc ID: {db_document.id}")
    except Exception as e:
        await db.rollback()
        print(f"Database Error: Failed to save document metadata: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save document metadata."
        )

    # Add the vector store processing as a background task
    background_tasks.add_task(
        add_to_vector_store_background,
        doc_id=db_document.id,
        user_id=current_user.id,
        text=extracted_text
    )
    print(f"Scheduled background task for vector embedding for doc_id {db_document.id}")

    return DocumentCreateResponse(doc_id=db_document.id, filename=file.filename)


@router.get(
    "/",
    response_model=DocumentListResponse,
    summary="List all documents uploaded by the current user"
)
async def list_user_documents(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """Retrieves a list of documents owned by the authenticated user."""
    query = (
        select(Document)
        .where(Document.owner_id == current_user.id)
        .order_by(Document.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    documents = result.scalars().all()
    return DocumentListResponse(documents=documents)


@router.get(
    "/{doc_id}",
    response_model=DocumentRead,
    summary="Get details of a specific document"
)
async def get_document_details(
    doc_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves details for a specific document owned by the authenticated user."""
    query = select(Document).where(Document.id == doc_id, Document.owner_id == current_user.id)
    result = await db.execute(query)
    document = result.scalar_one_or_none()

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {doc_id} not found or access denied."
        )
    return document


@router.delete(
    "/{doc_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a specific document"
)
async def delete_document(
    doc_id: int,
    background_tasks: BackgroundTasks, # To delete vectors in background
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Deletes a specific document owned by the authenticated user from the SQL database
    and schedules background deletion from the vector store.
    """
    # Find the document in SQL DB first to ensure ownership
    query = select(Document).where(Document.id == doc_id, Document.owner_id == current_user.id)
    result = await db.execute(query)
    document = result.scalar_one_or_none()

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {doc_id} not found or access denied for deletion."
        )

    # Delete from SQL DB
    try:
        await db.delete(document)
        await db.commit()
        print(f"Deleted document metadata (ID: {doc_id}) from SQL DB.")
    except Exception as e:
        await db.rollback()
        print(f"Database Error: Failed to delete document metadata: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document metadata."
        )

    # Schedule deletion from vector store in the background
    # Note: Vector store deletion might be slow or incomplete depending on implementation.
    background_tasks.add_task(
        delete_documents_from_store,
        doc_id=doc_id,
        user_id=current_user.id
    )
    print(f"Scheduled background task for vector store deletion for doc_id {doc_id}")

    return {"message": f"Document ID {doc_id} deletion process initiated."}
