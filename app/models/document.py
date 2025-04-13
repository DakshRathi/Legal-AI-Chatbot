# app/models/document.py
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, Dict, List, Any

# Model for response after successful document upload
class DocumentCreateResponse(BaseModel):
    doc_id: int
    filename: str
    message: str = "Document uploaded and processing started."

# Model for reading document details (excluding potentially large content)
class DocumentRead(BaseModel):
    id: int
    filename: str
    owner_id: int
    created_at: datetime
    metadata_json: Optional[Dict[str, Any]] = None # To show extracted entities

    # Pydantic V2 configuration for ORM compatibility
    model_config = ConfigDict(from_attributes=True)

# Model for listing documents
class DocumentListResponse(BaseModel):
    documents: List[DocumentRead]

