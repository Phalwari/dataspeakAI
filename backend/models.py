from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, JSON, Index, UniqueConstraint
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
    settings = relationship("TenantSettings", back_populates="tenant", uselist=False, cascade="all, delete-orphan")
    memberships = relationship("Membership", back_populates="tenant", cascade="all, delete-orphan")
    collections = relationship("Collection", back_populates="tenant", cascade="all, delete-orphan")
    query_templates = relationship("QueryTemplate", back_populates="tenant", cascade="all, delete-orphan")
    dashboards = relationship("Dashboard", back_populates="tenant", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="tenant", cascade="all, delete-orphan")
    metered_usages = relationship("MeteredUsage", back_populates="tenant", cascade="all, delete-orphan")
    rate_limits = relationship("RateLimit", back_populates="tenant", cascade="all, delete-orphan")
    security_policy = relationship("SecurityPolicy", back_populates="tenant", uselist=False, cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="tenant", cascade="all, delete-orphan")

class TenantSettings(Base):
    __tablename__ = "tenant_settings"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), unique=True, nullable=False)
    theme_mode = Column(String(20), default="light")
    custom_domain = Column(String(255), nullable=True)
    notifications_enabled = Column(Boolean, default=True)
    branding_logo_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    tenant = relationship("Tenant", back_populates="settings")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    role = Column(String, default="Admin") # Admin, Business Owner, Developer
    is_platform_admin = Column(Boolean, default=False, nullable=False)
    token_version = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    tenant = relationship("Tenant", back_populates="users")
    memberships = relationship("Membership", back_populates="user", cascade="all, delete-orphan")

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    permissions = relationship("Permission", back_populates="role", cascade="all, delete-orphan")
    memberships = relationship("Membership", back_populates="role")

class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    action = Column(String(50), nullable=False)    # read, write, delete, execute, manage
    resource = Column(String(50), nullable=False)  # databases, documents, queries, api_keys, users, all
    created_at = Column(DateTime, default=utc_now)

    role = relationship("Role", back_populates="permissions")

class Membership(Base):
    __tablename__ = "memberships"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="SET NULL"), nullable=True)
    is_owner = Column(Boolean, default=False)
    joined_at = Column(DateTime, default=utc_now)

    user = relationship("User", back_populates="memberships")
    tenant = relationship("Tenant", back_populates="memberships")
    role = relationship("Role", back_populates="memberships")

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
    secrets = relationship("Secret", back_populates="connection", cascade="all, delete-orphan")
    schemas = relationship("DatabaseSchema", back_populates="connection", cascade="all, delete-orphan")
    system_metrics = relationship("SystemMetric", back_populates="connection", cascade="all, delete-orphan")

class Secret(Base):
    __tablename__ = "secrets"

    id = Column(Integer, primary_key=True, index=True)
    connection_id = Column(Integer, ForeignKey("database_connections.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(50), default="local")
    encrypted_credentials = Column(Text, nullable=False)
    key_version = Column(String(50), nullable=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    connection = relationship("DatabaseConnection", back_populates="secrets")

class DatabaseSchema(Base):
    __tablename__ = "database_schemas"

    id = Column(Integer, primary_key=True, index=True)
    connection_id = Column(Integer, ForeignKey("database_connections.id", ondelete="CASCADE"), nullable=False)
    schema_name = Column(String(255), nullable=False, default="public")
    last_sync = Column(DateTime, default=utc_now)

    connection = relationship("DatabaseConnection", back_populates="schemas")
    tables = relationship("TableMetadata", back_populates="schema", cascade="all, delete-orphan")
    relationships = relationship("TableRelationship", back_populates="schema", cascade="all, delete-orphan")

class TableMetadata(Base):
    __tablename__ = "table_metadata"

    id = Column(Integer, primary_key=True, index=True)
    schema_id = Column(Integer, ForeignKey("database_schemas.id", ondelete="CASCADE"), nullable=False)
    table_name = Column(String(255), nullable=False, index=True)
    semantic_description = Column(Text, nullable=True)
    is_fact_table = Column(Boolean, default=False)
    kind = Column(String(50), default="table")  # "table" or "view"
    row_count_estimate = Column(Integer, default=0)

    schema = relationship("DatabaseSchema", back_populates="tables")
    columns = relationship("ColumnMetadata", back_populates="table", cascade="all, delete-orphan")

class ColumnMetadata(Base):
    __tablename__ = "column_metadata"

    id = Column(Integer, primary_key=True, index=True)
    table_id = Column(Integer, ForeignKey("table_metadata.id", ondelete="CASCADE"), nullable=False)
    column_name = Column(String(255), nullable=False, index=True)
    data_type = Column(String(100), nullable=False)
    is_pii = Column(Boolean, default=False)
    is_primary_key = Column(Boolean, default=False)
    is_foreign_key = Column(Boolean, default=False)
    foreign_key_target = Column(String(255), nullable=True)
    is_nullable = Column(Boolean, default=True)
    is_unique = Column(Boolean, default=False)
    sample_data = Column(JSON, nullable=True)
    unit_type = Column(String(50), nullable=True)

    table = relationship("TableMetadata", back_populates="columns")

class TableRelationship(Base):
    __tablename__ = "table_relationships"

    id = Column(Integer, primary_key=True, index=True)
    schema_id = Column(Integer, ForeignKey("database_schemas.id", ondelete="CASCADE"), nullable=False, index=True)
    kind = Column(String(50), default="foreign_key")  # "foreign_key" | "inferred"
    constraint_name = Column(String(255), nullable=True)
    source_table = Column(String(255), nullable=False)
    source_schema = Column(String(255), nullable=True)
    source_columns = Column(JSON, nullable=False)
    target_table = Column(String(255), nullable=False)
    target_schema = Column(String(255), nullable=True)
    target_columns = Column(JSON, nullable=False)

    __table_args__ = (
        Index("idx_table_relationships_schema_id", "schema_id"),
    )

    schema = relationship("DatabaseSchema", back_populates="relationships")

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
    document_associations = relationship("WidgetKeyDocument", back_populates="widget_key", cascade="all, delete-orphan")

class WidgetKeyDocument(Base):
    __tablename__ = "widget_key_documents"

    id = Column(Integer, primary_key=True, index=True)
    widget_key_id = Column(Integer, ForeignKey("widget_keys.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=utc_now)

    __table_args__ = (
        UniqueConstraint("widget_key_id", "document_id", name="uq_widget_key_document"),
    )

    widget_key = relationship("WidgetKey", back_populates="document_associations")
    document = relationship("Document", backref="widget_key_associations")

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
    parent_chunk_id = Column(Integer, ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=True)
    hierarchy_level = Column(Integer, default=1, nullable=False)  # 0 = parent (section/table), 1 = child (paragraph/leaf)
    created_at = Column(DateTime, default=utc_now)
    
    document = relationship("Document", back_populates="chunks")
    parent_chunk = relationship("DocumentChunk", remote_side=[id], backref="child_chunks")

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
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    database_id = Column(Integer, ForeignKey("database_connections.id", ondelete="SET NULL"), nullable=True)
    message_id = Column(Integer, ForeignKey("messages.id", ondelete="CASCADE"), nullable=True)
    raw_query = Column(Text, nullable=True)
    sql_generated = Column(Text, nullable=True)
    execution_time_ms = Column(Float, default=0.0)
    rows_returned = Column(Integer, default=0)
    status = Column(String, default="success") # success, failed, blocked
    was_successful = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    executed_at = Column(DateTime, default=utc_now)

    tenant = relationship("Tenant")
    user = relationship("User")
    database = relationship("DatabaseConnection")
    message = relationship("Message", back_populates="executed_queries")
    safety_logs = relationship("QuerySafetyLog", back_populates="executed_query", cascade="all, delete-orphan")

class QueryTemplate(Base):
    __tablename__ = "query_templates"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    sql_template = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    tenant = relationship("Tenant", back_populates="query_templates")

class QuerySafetyLog(Base):
    __tablename__ = "query_safety_logs"

    id = Column(Integer, primary_key=True, index=True)
    query_id = Column(Integer, ForeignKey("executed_queries.id", ondelete="CASCADE"), nullable=False)
    passed_validation = Column(Boolean, nullable=False, default=True)
    violation_details = Column(Text, nullable=True)
    checked_at = Column(DateTime, default=utc_now)

    executed_query = relationship("ExecutedQuery", back_populates="safety_logs")

class Intent(Base):
    __tablename__ = "intents"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    intent_name = Column(String(255), nullable=False)
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime, default=utc_now)

    message = relationship("Message", back_populates="intents")

class Collection(Base):
    __tablename__ = "collections"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    vector_provider = Column(String(50), default="faiss")
    created_at = Column(DateTime, default=utc_now)

    tenant = relationship("Tenant", back_populates="collections")
    vector_records = relationship("VectorRecord", back_populates="collection", cascade="all, delete-orphan")

class VectorRecord(Base):
    __tablename__ = "vector_records"

    id = Column(Integer, primary_key=True, index=True)
    chunk_id = Column(Integer, ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=False)
    collection_id = Column(Integer, ForeignKey("collections.id", ondelete="CASCADE"), nullable=False)
    vector_external_id = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now)

    chunk = relationship("DocumentChunk")
    collection = relationship("Collection", back_populates="vector_records")

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
    widget_key_id = Column(Integer, ForeignKey("widget_keys.id", ondelete="SET NULL"), nullable=True)
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
    summary_text = Column(Text, nullable=True)
    summary_turn_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    tenant = relationship("Tenant")
    user = relationship("User")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    shares = relationship("ConversationShare", back_populates="conversation", cascade="all, delete-orphan")

class ConversationShare(Base):
    __tablename__ = "conversation_shares"
    __table_args__ = (
        UniqueConstraint("conversation_id", "shared_with_user_id", name="uq_conversation_shares_conv_user"),
    )

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    shared_with_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    granted_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    conversation = relationship("Conversation", back_populates="shares")
    shared_with_user = relationship("User", foreign_keys=[shared_with_user_id])
    granted_by_user = relationship("User", foreign_keys=[granted_by_user_id])

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
    intents = relationship("Intent", back_populates="message", cascade="all, delete-orphan")
    executed_queries = relationship("ExecutedQuery", back_populates="message", cascade="all, delete-orphan")

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


class GeneratedInsight(Base):
    __tablename__ = "generated_insights"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    database_id = Column(Integer, ForeignKey("database_connections.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=False)
    category = Column(String(100), default="Operational")  # Revenue, Performance, Customer Success, Operational
    severity = Column(String(50), default="opportunity")   # critical, warning, alert, opportunity
    summary = Column(Text, nullable=False)
    impact_score = Column(Float, default=0.0)
    confidence_score = Column(Float, default=1.0)
    status = Column(String(50), default="active")          # active, dismissed, actioned
    created_at = Column(DateTime, default=utc_now)

    tenant = relationship("Tenant")
    database = relationship("DatabaseConnection")
    recommendations = relationship("Recommendation", back_populates="insight", cascade="all, delete-orphan")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    insight_id = Column(Integer, ForeignKey("generated_insights.id", ondelete="CASCADE"), nullable=False)
    action_step = Column(Text, nullable=False)
    priority = Column(String(20), default="medium")        # high, medium, low
    action_type = Column(String(50), default="general")    # navigate_logs, navigate_databases, navigate_analytics, general
    action_url = Column(String(255), nullable=True)
    status = Column(String(50), default="pending")         # pending, completed

    insight = relationship("GeneratedInsight", back_populates="recommendations")


class Dashboard(Base):
    __tablename__ = "dashboards"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    layout_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    tenant = relationship("Tenant", back_populates="dashboards")
    widgets = relationship("Widget", back_populates="dashboard", cascade="all, delete-orphan")

class Widget(Base):
    __tablename__ = "widgets"

    id = Column(Integer, primary_key=True, index=True)
    dashboard_id = Column(Integer, ForeignKey("dashboards.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(50), nullable=False)
    config_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    dashboard = relationship("Dashboard", back_populates="widgets")

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    stripe_id = Column(String(255), unique=True, index=True, nullable=True)
    plan_tier = Column(String(50), default="free")
    status = Column(String(50), default="active")
    current_period_end = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    tenant = relationship("Tenant", back_populates="subscriptions")
    invoices = relationship("Invoice", back_populates="subscription", cascade="all, delete-orphan")

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False)
    amount_due = Column(Float, nullable=False, default=0.0)
    billing_period_start = Column(DateTime, nullable=True)
    billing_period_end = Column(DateTime, nullable=True)
    status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=utc_now)

    subscription = relationship("Subscription", back_populates="invoices")
    payments = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    payment_method = Column(String(50), default="stripe")
    status = Column(String(50), default="succeeded")
    transaction_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    invoice = relationship("Invoice", back_populates="payments")

class MeteredUsage(Base):
    __tablename__ = "metered_usage"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    feature = Column(String(100), nullable=False)
    quantity = Column(Integer, default=0)
    recorded_at = Column(DateTime, default=utc_now)

    tenant = relationship("Tenant", back_populates="metered_usages")

class RateLimit(Base):
    __tablename__ = "rate_limits"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    endpoint_group = Column(String(100), nullable=False)
    max_requests_per_min = Column(Integer, default=60)
    created_at = Column(DateTime, default=utc_now)

    tenant = relationship("Tenant", back_populates="rate_limits")

class SecurityPolicy(Base):
    __tablename__ = "security_policies"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), unique=True, nullable=False)
    enforce_2fa = Column(Boolean, default=False)
    allowed_ip_ranges = Column(Text, nullable=True)
    pii_redaction_rules = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    tenant = relationship("Tenant", back_populates="security_policy")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(255), nullable=False)
    ip_address = Column(String(50), nullable=True)
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=utc_now)

    tenant = relationship("Tenant", back_populates="audit_logs")
    user = relationship("User")

class SystemMetric(Base):
    __tablename__ = "system_metrics"

    id = Column(Integer, primary_key=True, index=True)
    connection_id = Column(Integer, ForeignKey("database_connections.id", ondelete="CASCADE"), nullable=False)
    cpu_usage = Column(Float, default=0.0)
    memory_usage = Column(Float, default=0.0)
    active_connections = Column(Integer, default=0)
    timestamp = Column(DateTime, default=utc_now)

    connection = relationship("DatabaseConnection", back_populates="system_metrics")

