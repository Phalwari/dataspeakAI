---
title: Demo Databases, MariaDB Statement Timeout, and LLMGateway Model Fallback Order
date: 2026-10-20
touches:
  - backend/services/sql_agent.py
  - backend/services/sql_engine.py
  - backend/services/llm_generation_service.py
  - backend/services/connection_factory.py
---

# Demo Databases, MariaDB Statement Timeout, and LLMGateway Model Fallback Order

## Decided
- Provisioned three live containerized demonstration databases:
  1. PostgreSQL (`dataspeak_ecommerce` on port 5432) populated with customers, products, orders, order_items, and users alias view.
  2. MySQL / MariaDB (`retail_inventory` on port 3306) populated with warehouses, suppliers, inventory, and shipments.
  3. MongoDB (`analytics_store` on port 27017) populated with events, customer_feedback, and system_telemetry.
- Added `ALLOW_PRIVATE_DB_HOSTS=true` to `backend/.env` to allow safe local Docker container introspection in development without tripping SSRF loopback protections.
- Removed connection-time `init_command: SET SESSION MAX_EXECUTION_TIME=6000` from `sql_agent.py` for MariaDB/MySQL compatibility. MariaDB does not support MySQL 8's `MAX_EXECUTION_TIME` system variable and throws `OperationalError 1193` on connection handshake. Handled statement timeout via post-connection try/except and caller watchdog ceiling.
- Updated `GEMINI_MODELS` to active supported candidates (`gemini-3.6-flash`, `gemini-3.5-flash`, `gemini-3.8-flash`, `gemini-flash-latest`) and `GROQ_MODELS` to (`openai/gpt-oss-120b`, `openai/gpt-oss-20b`, `qwen/qwen3.8-27b`). Handled HTTP 404 gracefully so Groq falls through to available models.

## Tried and ruled out
- Tried passing `{"init_command": "SET SESSION MAX_EXECUTION_TIME=6000"}` in pymysql `connect_args`: crashed TCP connection handshake on MariaDB containers.
- Tried legacy `gemini-2.0-flash` and `gemini-2.5-flash`: Google Generative Language API now returns HTTP 404 stating models are no longer available to new users and advises using `gemini-3.x-flash`.

## Watch out
- Uvicorn on startup takes ~10 seconds to load HuggingFace `SentenceTransformer` embedding weights into memory before binding port 8000. Do not mark health checks failed during this warm-up window.
- Standalone scripts importing crypto or models must call `load_dotenv('backend/.env')` before importing `backend.services.crypto_service` to ensure `SECRET_KEY` is derived properly for Fernet decryption.
