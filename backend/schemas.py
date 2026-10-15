import re
from pydantic import BaseModel, EmailStr, model_validator, field_validator, Field, ConfigDict
from typing import Optional, List, Any, Dict
from datetime import datetime
from urllib.parse import urlparse, unquote

def _sanitize_and_validate_origin(origin_val: str) -> str:
    if not isinstance(origin_val, str):
        raise ValueError("Origin must be a string")
    origin_str = origin_val
    if origin_str == "*":
        raise ValueError("Wildcard origins ('*') are strictly disallowed for widget security")

    # Strictly disallow characters that could inject into CSP or HTTP headers (both literal and percent-encoded) (SEC-07)
    decoded_origin = unquote(origin_str)
    for forbidden_char in [";", ",", "\n", "\r", '"', "'", "*"]:
        if forbidden_char in origin_str or forbidden_char in decoded_origin:
            raise ValueError(f"Origin '{origin_str}' contains forbidden character '{forbidden_char}' (preventing header injection)")

    if origin_str != origin_str.strip() or any(c.isspace() for c in origin_str):
        raise ValueError(f"Origin '{origin_str}' cannot contain whitespace")

    if not (origin_str.lower().startswith("http://") or origin_str.lower().startswith("https://")):
        raise ValueError(f"Origin '{origin_str}' must start with http:// or https://")

    parsed = urlparse(origin_str)
    if not parsed.scheme or parsed.scheme.lower() not in ("http", "https"):
        raise ValueError(f"Origin '{origin_str}' must have a valid scheme (http or https)")
    if not parsed.netloc:
        raise ValueError(f"Origin '{origin_str}' has invalid hostname structure")
    if "@" in parsed.netloc:
        raise ValueError(f"Origin '{origin_str}' must not contain user credentials ('@')")
    if parsed.path and parsed.path != "/":
        raise ValueError(f"Origin '{origin_str}' must not include path segments ('{parsed.path}'). Specify only scheme, host, and optional port.")
    if parsed.query or parsed.params or parsed.fragment:
        raise ValueError(f"Origin '{origin_str}' must not include query parameters or fragments")

    if ":" in parsed.netloc:
        host, port_str = parsed.netloc.split(":", 1)
        try:
            port = int(port_str)
            if port < 1 or port > 65535:
                raise ValueError()
        except Exception:
            raise ValueError(f"Invalid port in origin '{origin_str}'")
        return f"{parsed.scheme.lower()}://{host.lower()}:{port}"

    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"

def validate_origin_item(origin: Any) -> str:
    if not isinstance(origin, str):
        raise ValueError("Origin must be a string")
    return _sanitize_and_validate_origin(origin)

class TenantBase(BaseModel):
    name: str
    website: Optional[str] = None
    industry: Optional[str] = None
    address: Optional[str] = None

class TenantResponse(TenantBase):
    id: int

    class Config:
        from_attributes = True

class TenantUpdate(BaseModel):
    website: Optional[str] = None
    industry: Optional[str] = None
    address: Optional[str] = None

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str
    company_name: Optional[str] = None
    invite_token: Optional[str] = None

class InviteCreate(BaseModel):
    email: EmailStr
    role: str = "Team Member"
    database_ids: Optional[list[int]] = None

class InviteResponse(BaseModel):
    invite_link: str
    email: EmailStr

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserChangePassword(BaseModel):
    current_password: str
    new_password: str

class UserResponse(UserBase):
    id: int
    role: str
    is_active: bool
    is_verified: bool
    tenant_id: Optional[int] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class DatabaseConnectionBase(BaseModel):
    name: Optional[str] = None
    db_name: Optional[str] = None
    db_type: str
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    database: Optional[str] = None
    connection_string: Optional[str] = None
    description: Optional[str] = None

class DatabaseConnectionCreate(DatabaseConnectionBase):
    password: Optional[str] = None

class DatabaseConnectionTest(BaseModel):
    db_type: str
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    connection_string: Optional[str] = None
    database: Optional[str] = None

class DatabaseConnectionTestResponse(BaseModel):
    success: bool
    message: str
    db_schema: Optional[Dict[str, Any]] = Field(default=None, alias="schema")

    class Config:
        populate_by_name = True

class AIConnectRequest(BaseModel):
    input_text: str
    db_name: Optional[str] = "Auto-Connected DB"

class DatabaseConnectionResponse(DatabaseConnectionBase):
    id: int
    status: str
    tables_metadata: Optional[Any] = None
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class ConnectionUpdate(BaseModel):
    name: Optional[str] = None
    db_name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    connection_string: Optional[str] = None
    database: Optional[str] = None
    description: Optional[str] = None

class TablePreviewRequest(BaseModel):
    table_name: Optional[str] = None
    table: Optional[str] = None
    limit: Optional[int] = 50
    filter: Optional[Dict[str, Any]] = None

class DBQueryRequest(BaseModel):
    query: str

class AIQueryRequest(BaseModel):
    question: str
    table_name: str

class TemplateAnalysisRequest(BaseModel):
    dataset_id: Any
    template_type: str

class TemplateAnalysisResponse(BaseModel):
    mapping: Dict[str, Any]
    column_info: List[Dict[str, Any]]
    processing_summary: Dict[str, Any]

class UserDatabaseAccessResponse(BaseModel):
    id: int
    user_id: int
    database_id: int

    class Config:
        from_attributes = True

class ApiKeyCreate(BaseModel):
    name: str
    description: Optional[str] = None

class ApiKeyResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    key: str
    status: str
    total_requests: int
    last_used_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True




class WidgetKeyCreate(BaseModel):
    name: str = "Default Widget Key"
    allowed_origins: List[str]
    monthly_message_cap: Optional[int] = 1000
    allow_sql: Optional[bool] = False
    allowed_database_ids: Optional[List[int]] = []
    allowed_tables: Optional[List[str]] = []

    @field_validator("allowed_origins")
    @classmethod
    def validate_allowed_origins(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("allowed_origins cannot be empty")
        return [validate_origin_item(o) for o in v]

class WidgetKeyUpdate(BaseModel):
    name: Optional[str] = None
    allowed_origins: Optional[List[str]] = None
    enabled: Optional[bool] = None
    monthly_message_cap: Optional[int] = None
    allow_sql: Optional[bool] = None
    allowed_database_ids: Optional[List[int]] = None
    allowed_tables: Optional[List[str]] = None

    @field_validator("allowed_origins")
    @classmethod
    def validate_allowed_origins(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return v
        if len(v) == 0:
            raise ValueError("allowed_origins cannot be empty if specified")
        return [validate_origin_item(o) for o in v]

class WidgetKeyResponse(BaseModel):
    id: int
    tenant_id: int
    public_key: str
    name: str
    allowed_origins: List[str]
    enabled: bool
    monthly_message_cap: int
    allow_sql: bool
    allowed_database_ids: Optional[List[int]] = None
    allowed_tables: Optional[List[str]] = None
    previous_key: Optional[str] = None
    previous_key_expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class WidgetKeyRotateResponse(BaseModel):
    id: int
    new_key: str
    previous_key: Optional[str] = None
    previous_key_expires_at: Optional[datetime] = None
    message: str

class WidgetSessionRequest(BaseModel):
    public_key: str
    conversation_id: Optional[int] = None

class WidgetSessionResponse(BaseModel):
    session_token: str
    expires_in: int
    tenant_id: int
    conversation_id: int

class ChatbotConfigBase(BaseModel):
    theme_color: str
    widget_title: str
    greeting_message: str
    position: str
    welcome_delay: int
    max_history: int
    sound_enabled: bool

class ChatbotConfigCreate(ChatbotConfigBase):
    pass

class ChatbotConfigResponse(ChatbotConfigBase):
    id: int
    tenant_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class DocumentBase(BaseModel):
    name: str
    file_type: str
    size: int
    status: str
    embeddings_count: int
    line_count: int = 0
    paragraph_count: int = 0
    table_count: int = 0
    image_count: int = 0
    progress: float = 0.0
    error_message: Optional[str] = None
    total_pages: int = 0
    pages_processed: int = 0
    visual_pages: int = 0
    celery_task_id: Optional[str] = None
    embedding_model: Optional[str] = "all-MiniLM-L6-v2"

class DocumentResponse(DocumentBase):
    id: int
    tenant_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class DocumentChunkResponse(BaseModel):
    id: int
    document_id: int
    content: str
    overlap_chars: int
    chunk_index: int
    page_number: Optional[int] = None
    content_type: str = "text"
    section_heading: Optional[str] = None
    reference_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class SearchQuery(BaseModel):
    query: str
    top_k: Optional[int] = 5
    synthesize: Optional[bool] = True
    document_ids: Optional[List[int]] = None
    content_types: Optional[List[str]] = None
    page_range: Optional[List[int]] = None
    search_mode: Optional[str] = "hybrid"
    re_rank: Optional[bool] = False

class SearchSynthesisResponse(BaseModel):
    query: str
    answer: Optional[str] = None
    results: List[dict] = []

class GithubLoginRequest(BaseModel):
    code: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp_code: str

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp_code: str
    new_password: str

class EmailVerificationRequest(BaseModel):
    email: EmailStr
    otp_code: str

class ResendVerificationRequest(BaseModel):
    email: EmailStr

class SchemaRegistryResponse(BaseModel):
    id: int
    connection_id: int
    table_name: str
    column_name: str
    data_type: str
    semantic_type: Optional[str] = "UNKNOWN"
    is_primary_key: Optional[bool] = False
    is_foreign_key: Optional[bool] = False
    foreign_key_target: Optional[str] = None
    is_measure: bool
    is_dimension: bool
    is_time_axis: bool
    cardinality: Optional[int] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    mean_value: Optional[float] = None
    null_percentage: float = 0.0

    class Config:
        from_attributes = True


class KpiDefinitionResponse(BaseModel):
    id: int
    tenant_id: int
    connection_id: int
    kpi_title: str
    aggregation_function: str
    target_column: str
    dimension_column: Optional[str] = None
    time_column: Optional[str] = None
    default_chart_type: str
    priority: Optional[int] = 1
    reasoning: Optional[str] = None

    class Config:
        from_attributes = True

class DashboardQueryRequest(BaseModel):
    database_id: Optional[int] = None
    table_name: Optional[str] = None
    target_column: Optional[str] = None
    dimension_column: Optional[str] = None
    aggregation: Optional[str] = "SUM"
    limit: Optional[int] = 10
    date_range: Optional[str] = "30days"
    filters: Optional[dict] = None

class AiInsightResponse(BaseModel):
    id: int
    tenant_id: int
    category: str
    title: str
    description: str
    severity: str
    confidence_score: int
    trend: str
    sparkline_values: Optional[list] = None
    created_at: datetime

    class Config:
        from_attributes = True

class NLQueryRequest(BaseModel):
    database_id: int
    query: str

class NLQueryResponse(BaseModel):
    query: str
    generated_sql: str
    explanation: str
    columns: List[str] = []
    rows: List[dict] = []
    row_count: int = 0
    execution_time_ms: float = 0.0
    status: str
    error_detail: Optional[str] = None

class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    sender_role: str
    content: str
    query_type: Optional[str] = "rag"
    metadata_json: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ConversationResponse(BaseModel):
    id: int
    tenant_id: int
    user_id: Optional[int] = None
    title: str
    platform: str
    created_at: datetime
    updated_at: datetime
    messages: Optional[List[MessageResponse]] = []

    class Config:
        from_attributes = True

class ConversationListItem(BaseModel):
    id: int
    title: str
    platform: str
    created_at: datetime
    updated_at: datetime
    last_message: Optional[str] = None
    message_count: int = 0

class ConversationUpdate(BaseModel):
    title: str

class ChatRequest(BaseModel):
    conversation_id: Optional[int] = None
    query: str
    source_preference: Optional[str] = "auto"
    database_id: Optional[int] = None
    stream: Optional[bool] = False

class SourceCitation(BaseModel):
    document_name: str
    page_number: Optional[int] = None
    content_type: str = "text"
    reference_id: Optional[str] = None
    snippet: str
    score: Optional[float] = 0.0
    grounding_score: Optional[float] = None
    is_grounded: Optional[bool] = None

class ChatResponse(BaseModel):
    conversation_id: int
    message_id: int
    user_message_id: int
    query: str
    answer: str
    query_type: str
    sources: List[SourceCitation] = []
    sql_data: Optional[Dict[str, Any]] = None
    grounding: Optional[Dict[str, Any]] = None
    sql_agent: Optional[Dict[str, Any]] = None
    created_at: datetime

class WidgetChatRequest(BaseModel):
    query: str
    session_token: Optional[str] = None
    conversation_id: Optional[int] = None
    stream: Optional[bool] = False

class WidgetChatResponse(BaseModel):
    conversation_id: int
    message_id: int
    query: str
    answer: str
    query_type: str
    sources: List[SourceCitation] = []
    created_at: datetime

class WidgetConfigResponse(BaseModel):
    theme_color: str = "#3b82f6"
    widget_title: str = "AI Assistant"
    greeting_message: str = "Hello! How can I help you today?"
    position: str = "bottom-right"
    welcome_delay: int = 1
    sound_enabled: bool = False



# ---------------------------------------------------------------------------
# Guided Reliability Dashboard Intelligence Schemas
# ---------------------------------------------------------------------------

class DomainTemplateResponse(BaseModel):
    id: str
    name: str
    description: str
    is_fallback: bool = False
    variable_count: int
    kpi_count: int


class SuggestMappingRequest(BaseModel):
    domain: Optional[str] = "generic"


class MappingSuggestionItem(BaseModel):
    variable: str
    display_name: str
    description: str
    required: bool
    column: Optional[str] = None  # e.g. "orders.total_amount"
    confidence: float
    semantic_type: Optional[str] = "UNKNOWN"
    reasoning: str


class SuggestMappingResponse(BaseModel):
    domain: str
    domain_name: str
    is_fallback: bool
    suggestions: List[MappingSuggestionItem]
    available_columns: List[dict]
    warnings: List[str] = []


class ApplyMappingRequest(BaseModel):
    domain: str
    mappings: Dict[str, Optional[str]] = {}  # e.g. {"revenue": "orders.total_amount", "order_date": "orders.created_at"}
    chart_preferences: Optional[List[str]] = None
    confirmed_by_user: Optional[bool] = False  # Explicit user confirmation flag

    @model_validator(mode="before")
    @classmethod
    def normalize_mappings_field(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "mappings" not in data and "mapping" in data:
                data["mappings"] = data["mapping"]
        return data


# ---------------------------------------------------------------------------
# Phase 1: Dashboard Overview, Query Logs, Usage & Admin Schemas
# ---------------------------------------------------------------------------

class OverviewQueryTimelinePoint(BaseModel):
    name: str
    date: str
    queries: int


class OverviewDatabaseActivity(BaseModel):
    name: str
    db_type: Optional[str] = None
    queries: int


class OverviewRecentQuery(BaseModel):
    id: int
    question: str
    database: str
    status: str
    time: str
    created_at: str


class AnalyticsOverviewResponse(BaseModel):
    total_queries: int
    connected_databases: int
    uploaded_documents: int
    api_calls_today: int
    subscription_plan: str
    query_data: List[OverviewQueryTimelinePoint]
    database_activity: List[OverviewDatabaseActivity]
    recent_queries: List[OverviewRecentQuery]


class QueryLogItem(BaseModel):
    id: int
    userQuestion: str
    generatedQuery: str
    database: str
    status: str
    executionTime: str
    timestamp: str
    rows: int
    tokens: Optional[int] = 0
    error: Optional[str] = None


class QueryLogsResponse(BaseModel):
    items: List[QueryLogItem]
    total: int
    page: int
    limit: int
    total_queries: int
    successful: int
    failed: int
    success_rate: float
    avg_response_time_ms: float


class UsageTimelinePoint(BaseModel):
    date: str
    queries: int
    tokens: int


class UsageDatabaseTypeDistribution(BaseModel):
    name: str
    value: int
    color: str


class UsageHourlyPoint(BaseModel):
    hour: str
    queries: int


class TenantUsageResponse(BaseModel):
    total_queries: int
    tokens_used: int
    token_limit: int
    available_tokens: int
    avg_tokens_per_query: float
    databases_count: int
    current_cost: str
    plan: Optional[str] = "Starter"
    usage_data: List[UsageTimelinePoint]
    database_type_data: List[UsageDatabaseTypeDistribution]
    hourly_data: List[UsageHourlyPoint]


class AdminPlatformStat(BaseModel):
    title: str
    value: str
    change: str
    trend: str
    key: str


class AdminStatsResponse(BaseModel):
    total_tenants: int
    total_users: int
    total_queries: int
    active_databases: int
    document_count: int
    platform_stats: List[AdminPlatformStat]
    platform_activity: Optional[List[OverviewQueryTimelinePoint]] = None


class AdminTenantItem(BaseModel):
    id: int
    company: str
    email: str
    plan: str
    queries: int
    databases: int
    users_count: int
    status: str
    joined: str
    usage: int


# ==========================================
# Phase 3: AI Insights & Recommendation Engine Schemas
# ==========================================

class RecommendationItem(BaseModel):
    id: int
    insight_id: int
    action_step: str
    priority: str = "medium"  # high, medium, low
    action_type: Optional[str] = "general"  # navigate_logs, navigate_databases, navigate_analytics, general
    action_url: Optional[str] = None
    status: str = "pending"  # pending, completed

    model_config = ConfigDict(from_attributes=True)


class RecommendationStatusUpdate(BaseModel):
    status: str  # pending, completed


class GeneratedInsightItem(BaseModel):
    id: int
    tenant_id: int
    database_id: Optional[int] = None
    database_name: Optional[str] = None
    title: str
    category: str  # Revenue, Performance, Customer Success, Operational
    severity: str  # critical, warning, alert, opportunity
    summary: str
    impact_score: float = 0.0
    confidence_score: float = 1.0
    status: str = "active"  # active, dismissed, actioned
    created_at: datetime
    recommendations: List[RecommendationItem] = []

    model_config = ConfigDict(from_attributes=True)


class GeneratedInsightStatusUpdate(BaseModel):
    status: str  # active, dismissed, actioned


class AIInsightsSummaryStats(BaseModel):
    total_insights: int = 0
    critical_count: int = 0
    opportunities_count: int = 0
    pending_actions_count: int = 0


class AIInsightsOverviewResponse(BaseModel):
    summary: AIInsightsSummaryStats
    insights: List[GeneratedInsightItem]
    available_categories: List[str] = ["All", "Revenue", "Performance", "Customer Success", "Operational"]
    has_connected_sources: bool = True


class AIInsightsRefreshResponse(BaseModel):
    message: str
    refreshed_count: int
    insights: List[GeneratedInsightItem]


# ==========================================
# Phase 4 - Stage 4A: RBAC, Settings & Catalog Schemas
# ==========================================

class TenantSettingsBase(BaseModel):
    theme_mode: Optional[str] = "light"
    custom_domain: Optional[str] = None
    notifications_enabled: Optional[bool] = True
    branding_logo_url: Optional[str] = None

class TenantSettingsUpdate(TenantSettingsBase):
    pass

class TenantSettingsResponse(TenantSettingsBase):
    id: int
    tenant_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PermissionBase(BaseModel):
    action: str
    resource: str

class PermissionCreate(PermissionBase):
    pass

class PermissionResponse(PermissionBase):
    id: int
    role_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None

class RoleCreate(RoleBase):
    pass

class RoleResponse(RoleBase):
    id: int
    created_at: datetime
    permissions: List[PermissionResponse] = []

    model_config = ConfigDict(from_attributes=True)


class MembershipBase(BaseModel):
    user_id: int
    tenant_id: int
    role_id: Optional[int] = None
    is_owner: bool = False

class MembershipCreate(MembershipBase):
    pass

class MembershipResponse(MembershipBase):
    id: int
    joined_at: datetime
    role: Optional[RoleResponse] = None

    model_config = ConfigDict(from_attributes=True)


class SecretResponse(BaseModel):
    id: int
    connection_id: int
    provider: str = "local"
    key_version: Optional[str] = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ColumnMetadataResponse(BaseModel):
    id: int
    table_id: int
    column_name: str
    data_type: str
    is_pii: bool = False
    is_primary_key: bool = False
    is_foreign_key: bool = False
    foreign_key_target: Optional[str] = None
    sample_data: Optional[Any] = None
    unit_type: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TableMetadataResponse(BaseModel):
    id: int
    schema_id: int
    table_name: str
    semantic_description: Optional[str] = None
    is_fact_table: bool = False
    row_count_estimate: int = 0
    columns: List[ColumnMetadataResponse] = []

    model_config = ConfigDict(from_attributes=True)


class DatabaseSchemaResponse(BaseModel):
    id: int
    connection_id: int
    schema_name: str
    last_sync: Optional[datetime] = None
    tables: List[TableMetadataResponse] = []

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Phase 4 - Stage 4B: Query Auditing, Safety & Vector Collections Schemas
# ==========================================

class QueryTemplateBase(BaseModel):
    name: str
    sql_template: str
    description: Optional[str] = None

class QueryTemplateCreate(QueryTemplateBase):
    pass

class QueryTemplateResponse(QueryTemplateBase):
    id: int
    tenant_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QuerySafetyLogResponse(BaseModel):
    id: int
    query_id: int
    passed_validation: bool
    violation_details: Optional[str] = None
    checked_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExecutedQueryAuditResponse(BaseModel):
    id: int
    tenant_id: int
    user_id: int
    database_id: Optional[int] = None
    message_id: Optional[int] = None
    sql_generated: Optional[str] = None
    execution_time_ms: float = 0.0
    rows_returned: int = 0
    status: str
    was_successful: bool = True
    error_message: Optional[str] = None
    executed_at: datetime
    safety_logs: List[QuerySafetyLogResponse] = []

    model_config = ConfigDict(from_attributes=True)


class IntentBase(BaseModel):
    intent_name: str
    confidence: float = 1.0

class IntentCreate(IntentBase):
    message_id: int

class IntentResponse(IntentBase):
    id: int
    message_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CollectionBase(BaseModel):
    name: str
    description: Optional[str] = None
    vector_provider: str = "faiss"

class CollectionCreate(CollectionBase):
    pass

class CollectionResponse(CollectionBase):
    id: int
    tenant_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VectorRecordBase(BaseModel):
    chunk_id: int
    collection_id: int
    vector_external_id: str

class VectorRecordCreate(VectorRecordBase):
    pass

class VectorRecordResponse(VectorRecordBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Phase 4 - Stage 4C: Custom Dashboards, Billing & Security Schemas
# ==========================================

class WidgetBase(BaseModel):
    type: str
    config_json: Optional[Any] = None

class WidgetCreate(WidgetBase):
    pass

class WidgetResponse(WidgetBase):
    id: int
    dashboard_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DashboardBase(BaseModel):
    title: str
    layout_json: Optional[Any] = None

class DashboardCreate(DashboardBase):
    pass

class DashboardUpdate(BaseModel):
    title: Optional[str] = None
    layout_json: Optional[Any] = None

class DashboardResponse(DashboardBase):
    id: int
    tenant_id: int
    created_at: datetime
    updated_at: datetime
    widgets: List[WidgetResponse] = []

    model_config = ConfigDict(from_attributes=True)


class SubscriptionBase(BaseModel):
    stripe_id: Optional[str] = None
    plan_tier: str = "free"
    status: str = "active"
    current_period_end: Optional[datetime] = None

class SubscriptionResponse(SubscriptionBase):
    id: int
    tenant_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvoiceBase(BaseModel):
    amount_due: float
    billing_period_start: Optional[datetime] = None
    billing_period_end: Optional[datetime] = None
    status: str = "pending"

class InvoiceResponse(InvoiceBase):
    id: int
    subscription_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaymentBase(BaseModel):
    payment_method: str = "stripe"
    status: str = "succeeded"
    transaction_id: Optional[str] = None

class PaymentResponse(PaymentBase):
    id: int
    invoice_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MeteredUsageCreate(BaseModel):
    feature: str
    quantity: int = 1

class MeteredUsageResponse(BaseModel):
    id: int
    tenant_id: int
    feature: str
    quantity: int
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RateLimitBase(BaseModel):
    endpoint_group: str
    max_requests_per_min: int = 60

class RateLimitCreate(RateLimitBase):
    pass

class RateLimitResponse(RateLimitBase):
    id: int
    tenant_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SecurityPolicyBase(BaseModel):
    enforce_2fa: bool = False
    allowed_ip_ranges: Optional[str] = None
    pii_redaction_rules: Optional[Any] = None

class SecurityPolicyUpdate(SecurityPolicyBase):
    pass

class SecurityPolicyResponse(SecurityPolicyBase):
    id: int
    tenant_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLogBase(BaseModel):
    action: str
    ip_address: Optional[str] = None
    details: Optional[Any] = None

class AuditLogCreate(AuditLogBase):
    user_id: Optional[int] = None

class AuditLogResponse(AuditLogBase):
    id: int
    tenant_id: int
    user_id: Optional[int] = None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class SystemMetricBase(BaseModel):
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    active_connections: int = 0

class SystemMetricCreate(SystemMetricBase):
    pass

class SystemMetricResponse(SystemMetricBase):
    id: int
    connection_id: int
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Phase 5: Entity-Relationship Diagram (ERD) & Schema Models
# ---------------------------------------------------------------------------

class ErdColumn(BaseModel):
    name: str
    type: str
    nullable: bool = True
    is_pk: bool = False
    is_fk: bool = False
    is_unique: bool = False


class ErdTable(BaseModel):
    id: str  # "schema.table" when schema applies, otherwise table name
    name: str
    schema_name: Optional[str] = Field(None, alias="schema")
    kind: str = "table"  # "table" | "view"
    columns: List[ErdColumn] = []

    model_config = ConfigDict(populate_by_name=True)


class ErdRelationship(BaseModel):
    id: str
    kind: str = "foreign_key"  # "foreign_key" | "inferred"
    constraint_name: Optional[str] = None
    confidence: Optional[float] = None
    reason: Optional[str] = None
    source_table: str
    source_columns: List[str]
    target_table: str
    target_columns: List[str]


class DatabaseErdResponse(BaseModel):
    database_id: int
    dialect: str
    schema_name: Optional[str] = Field(None, alias="schema")
    last_sync: Optional[datetime] = None
    source: str = "catalog"  # "catalog" | "live"
    truncated: bool = False
    table_count: int
    warnings: List[str] = []
    tables: List[ErdTable] = []
    relationships: List[ErdRelationship] = []

    model_config = ConfigDict(populate_by_name=True)
