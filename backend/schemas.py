import re
from pydantic import BaseModel, EmailStr, model_validator, field_validator, Field
from typing import Optional, List, Any, Dict
from datetime import datetime

ORIGIN_REGEX = re.compile(r"^https?://[A-Za-z0-9.-]+(?::[0-9]{1,5})?$", re.IGNORECASE)

def validate_origin_item(origin: Any) -> str:
    if not isinstance(origin, str):
        raise ValueError("Origin must be a string")
    if origin != origin.strip() or any(c.isspace() for c in origin):
        raise ValueError(f"Origin '{origin}' cannot contain whitespace")
    if ";" in origin or "," in origin or '"' in origin or "'" in origin or "*" in origin:
        raise ValueError(f"Origin '{origin}' contains invalid characters")
    if not ORIGIN_REGEX.match(origin):
        raise ValueError(
            f"Origin '{origin}' is invalid. Format must be http(s)://domain(:port) with no path, query, or special characters"
        )
    parts = origin.split("://", 1)
    scheme = parts[0].lower()
    rest = parts[1]
    if ":" in rest:
        host, port_str = rest.split(":", 1)
        try:
            port = int(port_str)
            if port < 1 or port > 65535:
                raise ValueError()
        except Exception:
            raise ValueError(f"Invalid port in origin '{origin}'")
        return f"{scheme}://{host.lower()}:{port}"
    return f"{scheme}://{rest.lower()}"

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

class SourceCitation(BaseModel):
    document_name: str
    page_number: Optional[int] = None
    content_type: str = "text"
    reference_id: Optional[str] = None
    snippet: str
    score: Optional[float] = 0.0

class ChatResponse(BaseModel):
    conversation_id: int
    message_id: int
    user_message_id: int
    query: str
    answer: str
    query_type: str
    sources: List[SourceCitation] = []
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


