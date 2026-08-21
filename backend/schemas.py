from pydantic import BaseModel, EmailStr
from typing import Optional
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
class DocumentResponse(DocumentBase):
    id: int
    tenant_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class SearchQuery(BaseModel):
    query: str

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
    is_measure: bool
    is_dimension: bool
    is_time_axis: bool
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

