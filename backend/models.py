from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, JSON
from sqlalchemy.orm import relationship
from database import Base
import datetime

class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    website = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    address = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    users = relationship("User", back_populates="tenant")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    role = Column(String, default="Admin") # Admin, Business Owner, Developer
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    tenant = relationship("Tenant", back_populates="users")

class UserDatabaseAccess(Base):
    __tablename__ = "user_database_access"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    database_id = Column(Integer, ForeignKey("database_connections.id"), nullable=False)

class TenantInvite(Base):
    __tablename__ = "tenant_invites"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True, nullable=False)
    token = Column(String, unique=True, index=True, nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    role = Column(String, default="Team Member")
    database_ids = Column(String, nullable=True) # Comma-separated list of database IDs
    expires_at = Column(DateTime, nullable=False)
    is_accepted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    tenant = relationship("Tenant")

class DatabaseConnection(Base):
    __tablename__ = "database_connections"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    name = Column(String, nullable=False)
    db_type = Column(String, nullable=False)
    host = Column(String, nullable=False)
    username = Column(String, nullable=False)
    password = Column(String, nullable=False) # Encrypted at rest using Fernet (backend/crypto.py)
    database = Column(String, nullable=False)
    status = Column(String, default="connected")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    tenant = relationship("Tenant")

class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    key = Column(String, unique=True, index=True, nullable=False)
    status = Column(String, default="active") # active, revoked
    total_requests = Column(Integer, default=0)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    tenant = relationship("Tenant")

class ChatbotConfig(Base):
    __tablename__ = "chatbot_configs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), unique=True, nullable=False)
    theme_color = Column(String, default="#3b82f6")
    widget_title = Column(String, default="AI Assistant")
    greeting_message = Column(String, default="Hi! I'm your AI assistant. Ask me anything about your data.")
    position = Column(String, default="bottom-right")
    welcome_delay = Column(Integer, default=3)
    max_history = Column(Integer, default=10)
    sound_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    tenant = relationship("Tenant")

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    name = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    size = Column(Integer, default=0)
    status = Column(String, default="Processing") # Completed, Processing, Failed
    embeddings_count = Column(Integer, default=0)
    line_count = Column(Integer, default=0)
    paragraph_count = Column(Integer, default=0)
    table_count = Column(Integer, default=0)
    image_count = Column(Integer, default=0)
    progress = Column(Float, default=0.0)         # 0.0 to 1.0 processing progress
    error_message = Column(Text, nullable=True)    # Diagnostic info on failure
    total_pages = Column(Integer, default=0)       # Total pages in document
    pages_processed = Column(Integer, default=0)   # Pages completed so far
    visual_pages = Column(Integer, default=0)      # Pages that required VLM processing
    celery_task_id = Column(String, nullable=True)
    embedding_model = Column(String, default="all-MiniLM-L6-v2")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    tenant = relationship("Tenant")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    content = Column(String, nullable=False)
    overlap_chars = Column(Integer, default=0)
    chunk_index = Column(Integer, nullable=False) # Good practice to keep chunks in order
    page_number = Column(Integer, nullable=True)       # Source page number (1-indexed)
    content_type = Column(String, default="text")       # "text" | "table" | "image"
    section_heading = Column(String, nullable=True)     # Nearest heading above this chunk
    reference_id = Column(String, nullable=True)        # e.g. "TABLE_REF_001", "FIGURE_REF_003"
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    document = relationship("Document", back_populates="chunks")

class PasswordResetOTP(Base):
    __tablename__ = "password_reset_otps"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True, nullable=False)
    otp_code = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class QueryLog(Base):
    __tablename__ = "query_logs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    database_id = Column(Integer, ForeignKey("database_connections.id"), nullable=True)
    natural_query = Column(Text, nullable=True)
    generated_sql = Column(Text, nullable=True)
    status = Column(String(50), default="success") # success, failed
    execution_time_ms = Column(Float, default=0.0)
    rows_returned = Column(Integer, default=0)
    tokens_used = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    tenant = relationship("Tenant")
    user = relationship("User")
    database = relationship("DatabaseConnection")

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    title = Column(String, default="New Conversation")
    platform = Column(String, default="web") # web, widget, api
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    tenant = relationship("Tenant")
    user = relationship("User")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    sender_role = Column(String(20), nullable=False) # user, assistant, system
    content = Column(Text, nullable=False)
    sanitized_content = Column(Text, nullable=True)
    query_type = Column(String(20), default="rag") # rag, sql, hybrid
    metadata_json = Column(JSON, nullable=True) # citations, SQL query, execution time, etc.
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")


