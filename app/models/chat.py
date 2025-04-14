# app/models/chat.py
from pydantic import BaseModel, ConfigDict
from typing import List
from datetime import datetime

# Model for chat request body (sending a message within a session)
class ChatMessageRequest(BaseModel):
    query: str
    session_id: int # Message must belong to a session

# Model for the response from the /chat POST endpoint
class ChatResponse(BaseModel):
    answer: str

# Model for representing a single message from the DB (used in history)
# Mirrors the updated ChatMessage SQLAlchemy model
class ChatMessageRead(BaseModel):
    id: int
    session_id: int # Linked to session
    message: str
    response: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True) # For ORM compatibility

# Model for the response from the /chat/history endpoint
class ChatHistoryResponse(BaseModel):
    history: List[ChatMessageRead]
