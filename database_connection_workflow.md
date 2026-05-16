# 📂 Module Documentation: Database & Tenant Management

This document outlines the inner workings of **Module 4 (Database Connection Management)** and its integration with **Module 2 (Tenant Onboarding)**.

---

## 🏗️ Module 4: Database Connection Workflow

The Database Connection module allows business owners to link their existing data sources to the AI platform. 

### 🔄 Connection Lifecycle (Sequence Diagram)

```mermaid
sequenceDiagram
    participant U as User (React UI)
    participant B as Backend (FastAPI)
    participant S as SQLAlchemy Engine
    participant DB as External DB (Postgres/MySQL)

    U->>B: POST /api/databases/test (Credentials)
    B->>S: create_engine(connection_url)
    S->>DB: connect() (TCP Handshake)
    alt Connection Success
        DB-->>S: Auth Granted
        S-->>B: Connection Object
        B-->>U: 200 OK (Connection Successful)
    else Connection Failed
        DB-->>S: Connection Refused/Auth Error
        S-->>B: Raise SQLAlchemyError
        B-->>U: 400 Bad Request (Error Detail)
    end
```

### 🛠️ Technical Implementation

#### 1. Connection String Generation
The backend dynamically constructs the connection string based on the selected database type:
- **PostgreSQL**: `postgresql://user:pass@host/dbname`
- **MySQL**: `mysql+pymysql://user:pass@host/dbname`

#### 2. The Validation Logic
Inside `backend/routers/databases.py`, the `test_database_connection` endpoint performs a real-time validation:

```python
# Simplified Logic
engine = create_engine(connection_url, connect_args={'connect_timeout': 5})
with engine.connect() as conn:
    # If this line executes, the DB is reachable
    pass
```

#### 3. Data Model
Connections are isolated by `tenant_id` to ensure data privacy.

| Field | Description |
| :--- | :--- |
| `name` | Friendly name (e.g., "Main Warehouse DB") |
| `db_type` | postgresql, mysql, mongodb, etc. |
| `host` | IP address or Domain of the server. |
| `status` | `connected` or `error`. |

---

## 🏢 Module 2: Tenant Onboarding Integration

Module 2 handles the high-level business profile. Database connections (Module 4) are children of a Tenant.

### 🔗 Relationship Overview

1.  **Onboarding**: A user signs up and creates a **Tenant** (Business profile).
2.  **Identity**: The user is assigned a `tenant_id`.
3.  **Ownership**: Every database connection added is stamped with that `tenant_id`.
4.  **Security**: The system filters all database queries:
    ```sql
    SELECT * FROM database_connections WHERE tenant_id = current_user.tenant_id;
    ```

### 🚀 Supported Real-Time Databases
Currently, the system is fully equipped to connect to:
- ✅ **PostgreSQL** (via `psycopg2`)
- ✅ **MySQL / MariaDB** (via `pymysql`)

*Planned for Phase 2: MongoDB, Firebase, and Oracle.*

---

## 🧪 How to Test Right Now
1.  Navigate to **Dashboard > Databases**.
2.  Click **Add Database**.
3.  Enter your local or cloud database credentials.
4.  Click **Test Connection**. 
5.  If successful, the status indicator will turn green, and the record will be saved to your local `app.db`.
