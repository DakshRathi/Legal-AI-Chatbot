# app/routers/chat.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.db.models import ChatMessage, User, ChatSession # Import DB models
from app.auth.dependencies import get_current_active_user # Import auth dependency
from app.models.chat import ChatMessageRequest, ChatResponse, ChatHistoryResponse, ChatMessageRead
from ml_core.qa_chain import get_rag_response # Import the RAG function

router = APIRouter()

@router.post(
    "/",
    response_model=ChatResponse,
    summary="Send a message within a specific chat session"
)
async def handle_chat_message(
    chat_request: ChatMessageRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Receives a user query for a specific chat session.
    Verifies session ownership.
    Invokes the RAG chain using documents linked to the session.
    Saves the query and response to the database, linked to the session.
    Returns the chatbot's answer.
    """
    user_id = current_user.id
    session_id = chat_request.session_id
    query = chat_request.query

    # --- Security Check: Verify session exists and belongs to the user ---
    # Fetch the session using its primary key
    session = await db.get(ChatSession, session_id)
    if not session or session.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found or access denied."
        )

    # Invoke the RAG chain - Pass session_id, RAG func will fetch doc_ids
    rag_result = await get_rag_response(query=query, user_id=user_id, session_id=session_id)
    answer = rag_result.get("answer", "Sorry, I could not process that request.")
    # context_docs = rag_result.get("context", []) # Optionally use context

    # Save the interaction, linking it to the verified session
    db_chat_message = ChatMessage(
        session_id=session_id, # Use the validated session_id
        message=query,
        response=answer
    )
    db.add(db_chat_message)
    try:
        await db.commit()
        print(f"Saved chat message for user {user_id}, session {session_id}")
    except Exception as e:
        await db.rollback()
        # Log the error; decide whether to inform the user
        print(f"Database Error: Failed to save chat message for session {session_id}: {e}")
        # Consider raising an error if saving is critical, but usually returning the answer is preferred
        # raise HTTPException(status_code=500, detail="Failed to save chat message.")

    # Return the answer from the RAG chain
    return ChatResponse(answer=answer)


@router.get(
    "/history/{session_id}",
    response_model=ChatHistoryResponse,
    summary="Get chat history for a specific session"
)
async def get_chat_history(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves the chat history for a specific session, ensuring the session
    belongs to the currently authenticated user.
    """
    # --- Security Check: Verify session exists and belongs to the user ---
    session = await db.get(ChatSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found or access denied."
        )

    # Fetch messages linked to the validated session
    query = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.timestamp.asc()) # Get messages in chronological order
    )
    result = await db.execute(query)
    history_db = result.scalars().all()

    # Use the ChatMessageRead Pydantic model for the response list
    history_response = [ChatMessageRead.model_validate(msg) for msg in history_db]

    return ChatHistoryResponse(history=history_response)
