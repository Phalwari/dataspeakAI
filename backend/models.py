from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, JSON, Text
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
    password = Column(String, nullable=False) # In production, this MUST be encrypted
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
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    document = relationship("Document", back_populates="chunks")

class PasswordResetOTP(Base):
    __tablename__ = "password_reset_otps"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True, nullable=False)
    otp_code = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class SchemaRegistry(Base):
    __tablename__ = "schema_registry"

    id = Column(Integer, primary_key=True, index=True)
    connection_id = Column(Integer, ForeignKey("database_connections.id"), nullable=False)
    table_name = Column(String, nullable=False, index=True)
    column_name = Column(String, nullable=False, index=True)
    data_type = Column(String, nullable=False)
    is_measure = Column(Boolean, default=False)
    is_dimension = Column(Boolean, default=False)
    is_time_axis = Column(Boolean, default=False)
    min_value = Column(Float, nullable=True)
    max_value = Column(Float, nullable=True)
    mean_value = Column(Float, nullable=True)
    null_percentage = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class KpiDefinition(Base):
    __tablename__ = "kpi_definitions"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    connection_id = Column(Integer, ForeignKey("database_connections.id"), nullable=False)
    kpi_title = Column(String, nullable=False)
    aggregation_function = Column(String, default="SUM") # SUM, AVG, COUNT, MAX, MIN
    target_column = Column(String, nullable=False)
    dimension_column = Column(String, nullable=True)
    time_column = Column(String, nullable=True)
    default_chart_type = Column(String, default="Line") # Line, Bar, Donut, Scatter
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class DashboardLayout(Base):
    __tablename__ = "dashboard_layouts"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    layout_name = Column(String, default="Default Layout")
    widget_positions = Column(JSON, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class AiInsight(Base):
    __tablename__ = "ai_insights"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    category = Column(String, default="General") # Sales, Revenue, Customer, Support, Inventory
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String, default="warning") # warning, alert, critical, success, opportunity
    confidence_score = Column(Integer, default=90)
    trend = Column(String, default="up") # up, down, neutral
    sparkline_values = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class ExecutedQuery(Base):
    __tablename__ = "executed_queries"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    database_id = Column(Integer, ForeignKey("database_connections.id"), nullable=True)
    raw_query = Column(Text, nullable=True)
    sql_generated = Column(Text, nullable=True)
    execution_time_ms = Column(Float, default=0.0)
    rows_returned = Column(Integer, default=0)
    status = Column(String, default="success") # success, failed, blocked
    error_message = Column(Text, nullable=True)
    executed_at = Column(DateTime, default=datetime.datetime.utcnow)

