from pydantic import BaseModel, EmailStr
from typing import Optional, List, Any, Dict
from datetime import datetime

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
    name: str
    db_type: str
    host: str
    username: str
    database: str

class DatabaseConnectionCreate(DatabaseConnectionBase):
    password: str

class DatabaseConnectionResponse(DatabaseConnectionBase):
    id: int
    status: str
    
    class Config:
        from_attributes = True

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
    sql_data: Optional[NLQueryResponse] = None
    created_at: datetime


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
    mappings: Dict[str, Optional[str]]  # e.g. {"revenue": "orders.total_amount", "order_date": "orders.created_at"}
    chart_preferences: Optional[List[str]] = None
    confirmed_by_user: Optional[bool] = False  # Explicit user confirmation flag

