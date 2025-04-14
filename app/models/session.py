# app/models/session.py
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime

# Model for creating a new session
class SessionCreate(BaseModel):
    session_name: Optional[str] = Field(default="New Chat", max_length=100) # Add length limit
    document_ids: Optional[List[int]] = [] # Allow linking docs on creation

# Model for reading/returning session info
class SessionRead(BaseModel):
    id: int
    session_name: str
    user_id: int
    created_at: datetime
    document_ids: List[int] = [] # IDs of linked documents

    model_config = ConfigDict(from_attributes=True) # For ORM compatibility

# Model for listing sessions
class SessionListResponse(BaseModel):
    sessions: List[SessionRead]

