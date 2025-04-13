from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, JSON
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime, timezone 

# Use declarative_base() directly from sqlalchemy.orm for modern SQLAlchemy
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False) # Added email field
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    documents = relationship("Document", back_populates="owner", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="owner", cascade="all, delete-orphan")

class Document(Base):
    __tablename__ = 'documents'

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    # We might store content separately or just metadata if content is large/in files
    # Let's omit 'content' column for now, assuming it's handled via file storage later
    # content = Column(Text, nullable=True) # Temporarily removed
    metadata_json = Column(JSON, nullable=True)  # Renamed from 'metadata' [5]
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationship
    owner = relationship("User", back_populates="documents")
    # Relationship to chat messages associated with this document
    chat_messages = relationship("ChatMessage", back_populates="document")

class ChatMessage(Base):
    __tablename__ = 'chat_messages'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    document_id = Column(Integer, ForeignKey('documents.id'), nullable=True)  # Optional link to a doc
    message = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    owner = relationship("User", back_populates="chat_messages")
    document = relationship("Document", back_populates="chat_messages") # Back-populate from Document
