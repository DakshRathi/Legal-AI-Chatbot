from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, JSON, Table
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime, timezone 

# Use declarative_base() directly from sqlalchemy.orm for modern SQLAlchemy
Base = declarative_base()

# Association Table for Session <-> Document Many-to-Many
session_documents_table = Table(
    "session_documents",
    Base.metadata,
    Column("session_id", Integer, ForeignKey("chat_sessions.id"), primary_key=True),
    Column("document_id", Integer, ForeignKey("documents.id"), primary_key=True),
)

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False) # Added email field
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    documents = relationship("Document", back_populates="owner", cascade="all, delete-orphan")
    sessions = relationship("ChatSession", back_populates="owner", cascade="all, delete-orphan")

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
    sessions = relationship(
        "ChatSession",
        secondary=session_documents_table,
        back_populates="documents"
    )

class ChatSession(Base):
    __tablename__ = 'chat_sessions'

    id = Column(Integer, primary_key=True, index=True)
    session_name = Column(String, default="New Chat")
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    owner = relationship("User", back_populates="sessions")
    # One-to-Many relationship with ChatMessage
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    # Many-to-Many relationship with Document
    documents = relationship(
        "Document",
        secondary=session_documents_table,
        back_populates="sessions"
    )

class ChatMessage(Base):
    __tablename__ = 'chat_messages'

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey('chat_sessions.id'), nullable=False)
    message = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    session = relationship("ChatSession", back_populates="messages")

