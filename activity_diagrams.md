# DataSpeakAI - Full Project Diagrams

This document contains Activity, Sequence, and ER diagrams for the DataSpeakAI platform.

---

## 📊 Activity Diagrams (Flowcharts)

These diagrams illustrate the logic and decision-making processes for each module.

### Module 1: User Authentication
```mermaid
flowchart TD
    Start([Start]) --> LoginSignup{Login or Signup?}
    LoginSignup -- Signup --> EnterDetails[Enter Email & Password]
    EnterDetails --> Validate[Validate Input]
    Validate --> CreateAccount[Create Pending Account]
    CreateAccount --> SendEmail[Send Verification Email]
    SendEmail --> ShowMsg[Show Check Email Message]
    ShowMsg --> End([End])

    LoginSignup -- Login --> EnterCreds[Enter Credentials]
    EnterCreds --> CheckCreds{Valid?}
    CheckCreds -- No --> Error[Show Invalid Credentials]
    CheckCreds -- Yes --> CheckVerified{Email Verified?}
    CheckVerified -- No --> VerifyError[Show Verify Email Error]
    CheckVerified -- Yes --> GenJWT[Generate JWT Token]
    GenJWT --> Redirect[Redirect to Dashboard]
    Redirect --> End
```

### Module 4 & 11: Database Connection & Schema Discovery
```mermaid
flowchart TD
    Start([Start]) --> NavDB[Navigate to Databases]
    NavDB --> AddDB[Click Add Database]
    AddDB --> EnterCreds[Enter DB Credentials]
    EnterCreds --> TestConn[Test Connection]
    TestConn --> Encrypt[Encrypt Credentials]
    Encrypt --> Attempt[Attempt Connection]
    Attempt --> Success{Success?}
    Success -- No --> ShowErr[Show Connection Error]
    Success -- Yes --> MarkActive[Mark DB as Active]
    MarkActive --> Discovery[Trigger Schema Discovery]
    Discovery --> End([End])
```

### Module 10 - 15: AI Query Engine (NL to SQL)
```mermaid
flowchart TD
    Start([Start]) --> SubNL[Submit NL Query]
    SubNL --> DetectIntent[Detect Intent]
    DetectIntent --> IsData{Is Data Query?}
    IsData -- No --> HandleOther[Handle non-data intent]
    IsData -- Yes --> FetchMeta[Fetch Metadata]
    FetchMeta --> SelectCols[Select Tables/Columns]
    SelectCols --> RouteQuery[Route to Template]
    RouteQuery --> GenSQL[Generate SQL]
    GenSQL --> ValidateSQL[Validate Safety]
    ValidateSQL --> ExecSQL[Execute on DB]
    ExecSQL --> ProcessRes[Process Results]
    ProcessRes --> GenNL[Generate NL Response]
    GenNL --> Display[Display to User]
    Display --> End([End])
```

### Module 17: Knowledge Base (RAG)
```mermaid
flowchart TD
    Start([Start]) --> NavKB[Navigate to Knowledge Base]
    NavKB --> Action{Upload or Search?}
    Action -- Upload --> UploadDoc[Upload PDF/TXT]
    UploadDoc --> Extract[Extract Text]
    Extract --> Chunk[Chunk Text]
    Chunk --> Embed[Generate Embeddings]
    Embed --> Upsert[Upsert to FAISS]
    Upsert --> End([End])

    Action -- Search --> SubQuery[Submit Semantic Query]
    SubQuery --> GenQueryEmbed[Generate Query Embedding]
    GenQueryEmbed --> SimSearch[Similarity Search]
    SimSearch --> Retrieve[Retrieve top-K Chunks]
    Retrieve --> RAGGen[Generate Response via RAG]
    RAGGen --> End
```

---

## 🔄 Sequence Diagrams

These diagrams show the interaction between the User, Frontend, Backend, and External Services.

### User Login Sequence
```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Backend
    participant Database
    participant JWT_Service

    User->>Frontend: Enter Credentials
    Frontend->>Backend: POST /auth/login
    Backend->>Database: Query User by Email
    Database-->>Backend: Return User Hash
    Backend->>Backend: Verify Password
    alt Valid Password
        Backend->>JWT_Service: Generate Token
        JWT_Service-->>Backend: Return JWT
        Backend-->>Frontend: 200 OK (JWT)
        Frontend->>User: Redirect to Dashboard
    else Invalid Password
        Backend-->>Frontend: 401 Unauthorized
        Frontend->>User: Show Error Message
    end
```

### AI Query Execution Sequence
```mermaid
sequenceDiagram
    participant User
    participant Chatbot_UI
    participant API_Gateway
    participant AI_Engine
    participant LLM_Service
    participant SQL_DB

    User->>Chatbot_UI: "Show me total sales for last month"
    Chatbot_UI->>API_Gateway: POST /api/query
    API_Gateway->>AI_Engine: Forward Request
    AI_Engine->>LLM_Service: Detect Intent & Extract Entities
    LLM_Service-->>AI_Engine: Intent: DataQuery, Period: LastMonth
    AI_Engine->>LLM_Service: Generate SQL (Prompt + Schema)
    LLM_Service-->>AI_Engine: SELECT SUM(total) FROM sales...
    AI_Engine->>SQL_DB: Execute SQL
    SQL_DB-->>AI_Engine: Result Set [ {total: 50000} ]
    AI_Engine->>LLM_Service: Format Results to NL
    LLM_Service-->>AI_Engine: "The total sales for last month were $50,000."
    AI_Engine-->>API_Gateway: Return JSON Response
    API_Gateway-->>Chatbot_UI: Return JSON Response
    Chatbot_UI->>User: Display Message
```

---

## 🗄️ ER Diagram (Database Structure)

```mermaid
erDiagram
    TENANT ||--o{ USER : owns
    TENANT ||--o{ DATABASE_CONN : manages
    TENANT ||--o{ API_KEY : generates
    TENANT ||--o{ DOCUMENT : uploads
    
    USER {
        string id PK
        string email
        string password_hash
        boolean is_verified
    }
    
    DATABASE_CONN {
        string id PK
        string name
        string engine
        string encrypted_creds
    }
    
    DOCUMENT {
        string id PK
        string filename
        string status
        datetime uploaded_at
    }
    
    API_KEY {
        string id PK
        string key_hash
        string name
        datetime expires_at
    }
```
