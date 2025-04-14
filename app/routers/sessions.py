# app/routers/sessions.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from typing import List, Optional

from app.db.database import get_db
from app.db.models import ChatSession, User, Document
from app.models.session import SessionCreate, SessionRead, SessionListResponse
from app.auth.dependencies import get_current_active_user


router = APIRouter()

@router.post(
    "/",
    response_model=SessionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new chat session"
)
async def create_session(
    session_data: SessionCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Creates a new chat session for the current user.
    Optionally links existing documents owned by the user to the session upon creation.
    """
    new_session = ChatSession(
        user_id=current_user.id,
        session_name=session_data.session_name or "New Chat" # Use provided name or default
    )

    # Validate and link documents if IDs are provided
    linked_docs = []
    if session_data.document_ids:
        # Query documents ensuring they exist and belong to the current user
        doc_query = select(Document).where(
            Document.owner_id == current_user.id,
            Document.id.in_(session_data.document_ids)
        )
        result = await db.execute(doc_query)
        linked_docs = result.scalars().all()

        # Check if all requested documents were found and owned by the user
        found_doc_ids = {doc.id for doc in linked_docs}
        if not set(session_data.document_ids).issubset(found_doc_ids):
            missing_ids = set(session_data.document_ids) - found_doc_ids
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"One or more document IDs not found or not owned by user: {missing_ids}"
            )
        # Add the validated documents to the session's relationship
        new_session.documents.extend(linked_docs)

    db.add(new_session)
    try:
        await db.commit()
        await db.refresh(new_session) # Get the generated ID and defaults
        # Re-fetch with eager loading to correctly populate document_ids in response
        # (SessionRead expects document_ids, which aren't loaded by default on refresh)
        query = (
            select(ChatSession)
            .options(selectinload(ChatSession.documents))
            .where(ChatSession.id == new_session.id)
        )
        refreshed_session = await db.scalar(query)
        if not refreshed_session: # Should not happen, but defensively check
            raise HTTPException(status_code=500, detail="Failed to retrieve session after creation.")

        print(f"Created session {refreshed_session.id} for user {current_user.id}")

        # Prepare response using the re-fetched session data
        return SessionRead(
            id=refreshed_session.id,
            session_name=refreshed_session.session_name,
            user_id=refreshed_session.user_id,
            created_at=refreshed_session.created_at,
            document_ids=[doc.id for doc in refreshed_session.documents] # Extract IDs
        )
    
    except Exception as e:
        await db.rollback()
        print(f"Database error creating session: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create chat session.")


@router.get(
    "/",
    response_model=SessionListResponse,
    summary="List all chat sessions for the current user"
)
async def list_sessions(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves all chat sessions owned by the authenticated user, including linked document IDs."""
    query = (
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id)
        .options(selectinload(ChatSession.documents)) # Eager load linked documents
        .order_by(ChatSession.created_at.desc()) # Show newest first
    )
    result = await db.execute(query)
    # Use unique() with scalars() when using eager loading on many-to-many to avoid duplicate sessions
    sessions = result.scalars().unique().all()

    # Format response using SessionRead model
    response_sessions = [
        SessionRead(
            id=s.id,
            session_name=s.session_name,
            user_id=s.user_id,
            created_at=s.created_at,
            document_ids=[doc.id for doc in s.documents] # Extract document IDs
        ) for s in sessions
    ]
    return SessionListResponse(sessions=response_sessions)


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_200_OK, # 200 OK or 204 No Content are suitable
    summary="Delete a chat session and its messages"
)
async def delete_session(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Deletes a specific chat session owned by the current user.
    Associated chat messages are deleted via database cascade.
    Links in session_documents table are also implicitly removed.
    """
    # Fetch the session first to verify ownership
    query = select(ChatSession).where(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    )
    result = await db.execute(query)
    session_to_delete = result.scalar_one_or_none()

    if session_to_delete is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or access denied."
        )

    # Delete the session. Cascades should handle ChatMessages.
    # Associations in session_documents are typically handled by the DB relationship itself.
    try:
        await db.delete(session_to_delete)
        await db.commit()
        print(f"Deleted session {session_id} for user {current_user.id}")
        return {"message": f"Session ID {session_id} deleted successfully."}
    except Exception as e:
        await db.rollback()
        print(f"Database error deleting session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not delete chat session."
        )
