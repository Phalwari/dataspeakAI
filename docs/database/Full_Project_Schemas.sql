-- ==========================================
-- 1. TENANT MANAGEMENT SCHEMA
-- ==========================================

CREATE TABLE tenants (
    id SERIAL PRIMARY KEY,
    org_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    industry VARCHAR(100),
    website VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE tenant_settings (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
    theme_mode VARCHAR(20) DEFAULT 'light',
    custom_domain VARCHAR(255),
    notifications_enabled BOOLEAN DEFAULT TRUE,
    branding_logo_url VARCHAR(500)
);

-- ==========================================
-- 2. USER & ACCESS CONTROL SCHEMA
-- ==========================================

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_verified BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    description TEXT
);

CREATE TABLE permissions (
    id SERIAL PRIMARY KEY,
    role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL,
    resource VARCHAR(50) NOT NULL
);

CREATE TABLE memberships (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
    role_id INTEGER REFERENCES roles(id),
    is_owner BOOLEAN DEFAULT FALSE,
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- 3. DATABASE CONNECTION & METADATA SCHEMA
-- ==========================================

CREATE TABLE database_connections (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    engine VARCHAR(50) NOT NULL,
    host VARCHAR(255) NOT NULL,
    port INTEGER,
    db_name VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'connected',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE secrets (
    id SERIAL PRIMARY KEY,
    connection_id INTEGER REFERENCES database_connections(id) ON DELETE CASCADE,
    provider VARCHAR(50) DEFAULT 'local',
    encrypted_credentials TEXT NOT NULL,
    key_version VARCHAR(50),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE database_schemas (
    id SERIAL PRIMARY KEY,
    connection_id INTEGER REFERENCES database_connections(id) ON DELETE CASCADE,
    schema_name VARCHAR(255) NOT NULL,
    last_sync TIMESTAMP WITH TIME ZONE
);

CREATE TABLE table_metadata (
    id SERIAL PRIMARY KEY,
    schema_id INTEGER REFERENCES database_schemas(id) ON DELETE CASCADE,
    table_name VARCHAR(255) NOT NULL,
    semantic_description TEXT,
    is_fact_table BOOLEAN DEFAULT FALSE,
    row_count_estimate INTEGER
);

CREATE TABLE column_metadata (
    id SERIAL PRIMARY KEY,
    table_id INTEGER REFERENCES table_metadata(id) ON DELETE CASCADE,
    column_name VARCHAR(255) NOT NULL,
    data_type VARCHAR(100) NOT NULL,
    is_pii BOOLEAN DEFAULT FALSE,
    is_primary_key BOOLEAN DEFAULT FALSE,
    is_foreign_key BOOLEAN DEFAULT FALSE,
    foreign_key_target VARCHAR(255),
    sample_data JSONB,
    unit_type VARCHAR(50)
);

-- ==========================================
-- 4. AI ENGINE & CHATBOT SCHEMA
-- ==========================================

CREATE TABLE chatbot_configs (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER UNIQUE REFERENCES tenants(id) ON DELETE CASCADE,
    widget_title VARCHAR(100) DEFAULT 'AI Assistant',
    theme_color VARCHAR(20) DEFAULT '#3b82f6',
    greeting_message TEXT,
    position VARCHAR(20) DEFAULT 'bottom-right',
    welcome_delay INTEGER DEFAULT 3,
    max_history INTEGER DEFAULT 10,
    sound_enabled BOOLEAN DEFAULT TRUE
);

CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    platform VARCHAR(50) DEFAULT 'web',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER REFERENCES conversations(id) ON DELETE CASCADE,
    sender_role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    sanitized_content TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE intents (
    id SERIAL PRIMARY KEY,
    message_id INTEGER REFERENCES messages(id) ON DELETE CASCADE,
    intent_name VARCHAR(255),
    confidence FLOAT
);

CREATE TABLE query_templates (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    sql_template TEXT NOT NULL,
    description TEXT
);

CREATE TABLE executed_queries (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    database_id INTEGER REFERENCES database_connections(id) ON DELETE SET NULL,
    message_id INTEGER REFERENCES messages(id) ON DELETE CASCADE,
    raw_query TEXT,
    sql_generated TEXT,
    execution_time_ms FLOAT,
    rows_returned INTEGER,
    status VARCHAR(50) DEFAULT 'success',
    was_successful BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE query_safety_logs (
    id SERIAL PRIMARY KEY,
    query_id INTEGER REFERENCES executed_queries(id) ON DELETE CASCADE,
    passed_validation BOOLEAN NOT NULL,
    violation_details TEXT,
    checked_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- 5. KNOWLEDGE BASE (RAG) SCHEMA
-- ==========================================

CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    file_type VARCHAR(50),
    status VARCHAR(50) DEFAULT 'processing',
    total_tokens INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE document_chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    chunk_index INTEGER NOT NULL
);

CREATE TABLE collections (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    vector_provider VARCHAR(50) DEFAULT 'faiss',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE vector_records (
    id SERIAL PRIMARY KEY,
    chunk_id INTEGER REFERENCES document_chunks(id) ON DELETE CASCADE,
    collection_id INTEGER REFERENCES collections(id) ON DELETE CASCADE,
    vector_external_id VARCHAR(255) NOT NULL
);

-- ==========================================
-- 6. AI INSIGHTS & ANALYTICS SCHEMA
-- ==========================================

CREATE TABLE generated_insights (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
    category VARCHAR(100),
    summary TEXT NOT NULL,
    impact_score FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE recommendations (
    id SERIAL PRIMARY KEY,
    insight_id INTEGER REFERENCES generated_insights(id) ON DELETE CASCADE,
    action_step TEXT NOT NULL,
    priority VARCHAR(20)
);

CREATE TABLE dashboards (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    layout_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE widgets (
    id SERIAL PRIMARY KEY,
    dashboard_id INTEGER REFERENCES dashboards(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    config_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- 7. BILLING & SUBSCRIPTION SCHEMA
-- ==========================================

CREATE TABLE subscriptions (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
    stripe_id VARCHAR(255) UNIQUE,
    plan_tier VARCHAR(50) DEFAULT 'free',
    status VARCHAR(50) DEFAULT 'active',
    current_period_end TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE invoices (
    id SERIAL PRIMARY KEY,
    subscription_id INTEGER REFERENCES subscriptions(id) ON DELETE CASCADE,
    amount_due DECIMAL(10, 2) NOT NULL,
    billing_period_start TIMESTAMP WITH TIME ZONE,
    billing_period_end TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    invoice_id INTEGER REFERENCES invoices(id) ON DELETE CASCADE,
    payment_method VARCHAR(50),
    status VARCHAR(50),
    transaction_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE metered_usage (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
    feature VARCHAR(100) NOT NULL,
    quantity INTEGER DEFAULT 0,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- 8. API & SECURITY SCHEMA
-- ==========================================

CREATE TABLE api_keys (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255),
    hashed_key VARCHAR(255) UNIQUE NOT NULL,
    scopes JSONB,
    expires_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE rate_limits (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
    endpoint_group VARCHAR(100),
    max_requests_per_min INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE security_policies (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
    enforce_2fa BOOLEAN DEFAULT FALSE,
    allowed_ip_ranges TEXT,
    pii_redaction_rules JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- 9. MONITORING & AUDIT SCHEMA
-- ==========================================

CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(255) NOT NULL,
    ip_address VARCHAR(50),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE system_metrics (
    id SERIAL PRIMARY KEY,
    connection_id INTEGER REFERENCES database_connections(id) ON DELETE CASCADE,
    cpu_usage FLOAT,
    memory_usage FLOAT,
    active_connections INTEGER,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
