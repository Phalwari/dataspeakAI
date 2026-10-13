from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, JSON, Index
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime, timezone

def utc_now():
    return datetime.now(timezone.utc)

class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    website = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    address = Column(String, nullable=True)
    plan = Column(String(50), default="Starter")
    created_at = Column(DateTime, default=utc_now)

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
    created_at = Column(DateTime, default=utc_now)

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
    created_at = Column(DateTime, default=utc_now)

    tenant = relationship("Tenant")

class DatabaseConnection(Base):
    __tablename__ = "database_connections"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    name = Column(String, nullable=False)
    db_type = Column(String, nullable=False)
    host = Column(String, nullable=True)
    username = Column(String, nullable=True)
    password = Column(String, nullable=True) # Encrypted at rest using Fernet
    database = Column(String, nullable=True)
    port = Column(Integer, nullable=True)
    connection_string = Column(String, nullable=True)
    tables_metadata = Column(JSON, nullable=True)
    insights_cache = Column(JSON, nullable=True)
    insights_cached_at = Column(DateTime, nullable=True)
    description = Column(String, nullable=True)
    status = Column(String, default="connected")
    created_at = Column(DateTime, default=utc_now)
    
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
    created_at = Column(DateTime, default=utc_now)
    
    tenant = relationship("Tenant")

class WidgetKey(Base):
    __tablename__ = "widget_keys"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    public_key = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(100), default="Default Widget")
    allowed_origins = Column(JSON, nullable=False, default=list) # e.g. ["https://example.com"]
    enabled = Column(Boolean, default=True)
    monthly_message_cap = Column(Integer, default=1000)
    allow_sql = Column(Boolean, default=False)
    allowed_database_ids = Column(JSON, nullable=True, default=list)
    allowed_tables = Column(JSON, nullable=True, default=list)
    previous_key = Column(String(64), nullable=True)
    previous_key_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

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
    created_at = Column(DateTime, default=utc_now)
    
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
    created_at = Column(DateTime, default=utc_now)
    tenant = relationship("Tenant")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    content = Column(String, nullable=False)
    overlap_chars = Column(Integer, default=0)
    chunk_index = Column(Integer, nullable=False)
    page_number = Column(Integer, nullable=True)
    content_type = Column(String, default="text")       # "text" | "table" | "image"
    section_heading = Column(String, nullable=True)
    reference_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    
    document = relationship("Document", back_populates="chunks")

class PasswordResetOTP(Base):
    __tablename__ = "password_reset_otps"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True, nullable=False)
    otp_code = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=utc_now)

class SchemaRegistry(Base):
    __tablename__ = "schema_registry"

    id = Column(Integer, primary_key=True, index=True)
    connection_id = Column(Integer, ForeignKey("database_connections.id"), nullable=False)
    table_name = Column(String, nullable=False, index=True)
    column_name = Column(String, nullable=False, index=True)
    data_type = Column(String, nullable=False)
    semantic_type = Column(String, default="UNKNOWN", nullable=True) # ID, UUID, DATE, DATETIME, NUMERIC_MEASURE, CURRENCY/AMOUNT, CATEGORY, TEXT, BOOLEAN, UNKNOWN
    is_primary_key = Column(Boolean, default=False)
    is_foreign_key = Column(Boolean, default=False)
    foreign_key_target = Column(String, nullable=True) # e.g. "customers.id"
    is_measure = Column(Boolean, default=False)
    is_dimension = Column(Boolean, default=False)
    is_time_axis = Column(Boolean, default=False)
    cardinality = Column(Integer, nullable=True)
    min_value = Column(Float, nullable=True)
    max_value = Column(Float, nullable=True)
    mean_value = Column(Float, nullable=True)
    null_percentage = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

class KpiDefinition(Base):
    __tablename__ = "kpi_definitions"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    connection_id = Column(Integer, ForeignKey("database_connections.id"), nullable=False)
    kpi_title = Column(String, nullable=False)
    aggregation_function = Column(String, nullable=True) # SUM, AVG, COUNT, MAX, MIN, COUNT_DISTINCT
    target_column = Column(String, nullable=False)
    dimension_column = Column(String, nullable=True)
    time_column = Column(String, nullable=True)
    default_chart_type = Column(String, default="Line") # Line, Bar, Donut, Scatter, Funnel, etc.
    priority = Column(Integer, default=1)
    reasoning = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

class DashboardLayout(Base):
    __tablename__ = "dashboard_layouts"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    connection_id = Column(Integer, ForeignKey("database_connections.id"), nullable=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    source_type = Column(String, default="database") # database, document
    source_archetype = Column(String, default="relational_sql") # relational_timeseries, relational_categorical, tabular_spreadsheet, document_knowledge
    layout_name = Column(String, default="Default Layout")
    business_domain = Column(String, nullable=True)
    domain_mapping = Column(JSON, nullable=True) # Confirmed variable-to-column mappings
    widget_positions = Column(JSON, nullable=True)
    charts_config = Column(JSON, nullable=True)
    filters_config = Column(JSON, nullable=True)
    validation_warnings = Column(JSON, nullable=True)
    used_fallback = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

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
    created_at = Column(DateTime, default=utc_now)

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
    executed_at = Column(DateTime, default=utc_now)

class QueryLog(Base):
    __tablename__ = "query_logs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    widget_key_id = Column(Integer, ForeignKey("widget_keys.id"), nullable=True, index=True)
    database_id = Column(Integer, ForeignKey("database_connections.id"), nullable=True)
    natural_query = Column(Text, nullable=True)
    generated_sql = Column(Text, nullable=True)
    status = Column(String(50), default="success")
    execution_time_ms = Column(Float, default=0.0)
    rows_returned = Column(Integer, default=0)
    tokens_used = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    source = Column(String(50), default="web")
    created_at = Column(DateTime, default=utc_now)

    __table_args__ = (
        Index("idx_query_logs_widget_key_created", "widget_key_id", "created_at"),
    )

    tenant = relationship("Tenant")
    user = relationship("User")
    database = relationship("DatabaseConnection")
    widget_key = relationship("WidgetKey")

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    title = Column(String, default="New Conversation")
    platform = Column(String, default="web")
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    tenant = relationship("Tenant")
    user = relationship("User")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    sender_role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    sanitized_content = Column(Text, nullable=True)
    query_type = Column(String(20), default="rag")
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    conversation = relationship("Conversation", back_populates="messages")

class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    name = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # csv, xlsx, etc.
    file_path = Column(String, nullable=False)
    file_size = Column(String, nullable=False)
    columns = Column(JSON, nullable=False)
    row_count = Column(Integer, nullable=False)
    analysis_results = Column(JSON, nullable=True)
    indexing_status = Column(String, default="ready")
    ml_insights_cache = Column(JSON, nullable=True)
    ml_insights_cached_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    tenant = relationship("Tenant")
    owner = relationship("User")

