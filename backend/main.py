import sys
import os

# Ensure backend directory is in sys.path when imported from root or elsewhere
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi import FastAPI, Request, Depends
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send
from sqlalchemy.orm import Session
import models
from database import engine, get_db
from dependencies import get_current_admin_user
from routers import (
    users, tenants, databases, api_keys, chatbot_config, documents,
    query, chat, analytics, connections, insights, files, file_insights,
    widget, erd
)
from dotenv import load_dotenv

load_dotenv()

# Production security assertion
if os.getenv("ENVIRONMENT", "").lower() == "production":
    if not os.getenv("WIDGET_HMAC_SECRET"):
        raise RuntimeError(
            "CRITICAL SECURITY CONFIGURATION ERROR: WIDGET_HMAC_SECRET must be explicitly set when ENVIRONMENT=production. Application startup aborted."
        )

# Check secret key
SECRET_KEY = os.getenv("SECRET_KEY", "dataspeakai-default-encryption-secret-key-32b")
if not SECRET_KEY:
    print("[WARNING] SECRET_KEY environment variable not set. Using fallback for development.")

# Startup database check and lifecycle control
env_mode = os.getenv("ENVIRONMENT", "development").lower()

if env_mode == "production":
    from scripts.schema_preflight import inspect_database_layout
    report = inspect_database_layout(engine)
    if report["layout"] != "LAYOUT_CURRENT":
        raise RuntimeError(
            f"Database schema preflight failed on startup: Layout '{report['layout']}' is not ready for production serving. "
            f"Details: {report.get('details', '')}. Explicitly run 'python backend/scripts/migrate.py upgrade' before starting the application."
        )
    print(f"[STARTUP] Production database preflight OK (Layout: {report['layout']}, Rev: {report['alembic_revision']})")
else:
    # Development / Test mode convenience
    if os.getenv("ENABLE_DEV_STARTUP_DDL", "true").lower() == "true":
        models.Base.metadata.create_all(bind=engine)
        try:
            from services.db_migration import run_schema_migrations
            run_schema_migrations(engine)
        except Exception as e:
            print(f"[MIGRATION] Dev startup schema sync note: {e}")
        try:
            from scripts.seed_admin import seed_superadmin
            seed_superadmin()
        except Exception as e:
            print(f"[STARTUP] Superadmin seed note: {e}")

# Startup embedding model warm-up (controlled by EMBEDDING_WARMUP, default true in non-test)
try:
    from routers.chat import warmup_embeddings
    warmup_embeddings()
except Exception as e:
    print(f"[EMBEDDING WARMUP] Note: {e}")

app = FastAPI(title="DataSpeakAI Platform API")


def get_dashboard_cors_origins() -> list[str]:
    raw_cors = os.getenv("CORS_ORIGINS", "")
    if raw_cors and raw_cors.strip():
        origins = [o.strip() for o in raw_cors.split(",") if o.strip()]
    else:
        origins = [
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
        ]
    # Filter out wildcard "*" to eliminate browser credential reflection risks
    filtered_origins = [o for o in origins if o != "*"]
    if os.getenv("ENVIRONMENT", "").lower() == "production" and not filtered_origins:
        raise RuntimeError(
            "CRITICAL SECURITY CONFIGURATION ERROR: CORS_ORIGINS must be explicitly configured with trusted hostnames in production. Wildcards are forbidden."
        )
    return filtered_origins


class DecoupledCORSMiddleware(CORSMiddleware):
    """
    Decoupled CORS Architecture (Task NR-1.1-A-T08):
    - Dashboard routes (/api/auth, /api/tenant, /api/conversations, /api/databases, etc.)
      strictly enforce the configured explicit dashboard origin allowlist with allow_credentials=True.
      Unauthorized origins cannot receive credentialed responses or succeed at preflights.
    - Standalone widget visitor routes (/api/widget/*, /api/chat/widget, /widget.js, /embed/*)
      support cross-origin requests from host websites without browser credentials,
      delegating origin authorization strictly to the publishable key's allowed_origins registry.
    """

    def __init__(
        self,
        app: ASGIApp,
        allow_origins: list[str],
        allow_credentials: bool = True,
        allow_methods: list[str] = None,
        allow_headers: list[str] = None,
        max_age: int = 600,
    ):
        self.max_age_val = max_age
        super().__init__(
            app=app,
            allow_origins=allow_origins,
            allow_credentials=allow_credentials,
            allow_methods=allow_methods or ["*"],
            allow_headers=allow_headers or ["*"],
            max_age=max_age,
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        is_widget_endpoint = (
            path.startswith("/api/widget")
            or path == "/api/chat/widget"
            or path == "/widget.js"
            or path.startswith("/embed")
        )

        headers = Headers(scope=scope)
        origin = headers.get("origin")
        method = scope.get("method")

        if not is_widget_endpoint:
            # Delegate strictly to standard CORSMiddleware with dashboard allowlist & credentials
            async def dashboard_send_wrapper(message: Message) -> None:
                if message["type"] == "http.response.start":
                    message.setdefault("headers", [])
                    res_headers = MutableHeaders(scope=message)
                    if origin and not self.is_allowed_origin(origin):
                        # Ensure unauthorized dashboard origins NEVER receive credential reflection
                        if "access-control-allow-credentials" in res_headers:
                            del res_headers["access-control-allow-credentials"]
                await send(message)

            await super().__call__(scope, receive, dashboard_send_wrapper)
            return

        # Handle widget visitor endpoints without browser credentials
        if origin is not None and method == "OPTIONS" and "access-control-request-method" in headers:
            requested_headers = headers.get("access-control-request-headers", "*")
            preflight_headers = {
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
                "Access-Control-Allow-Headers": requested_headers or "*",
                "Access-Control-Max-Age": str(self.max_age_val),
                "Vary": "Origin",
            }
            res = PlainTextResponse("OK", status_code=200, headers=preflight_headers)
            await res(scope, receive, send)
            return

        async def widget_send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                message.setdefault("headers", [])
                res_headers = MutableHeaders(scope=message)
                if origin:
                    res_headers["Access-Control-Allow-Origin"] = origin
                    existing_vary = res_headers.getlist("Vary")
                    if "Origin" not in existing_vary:
                        res_headers["Vary"] = ", ".join([*existing_vary, "Origin"]) if existing_vary else "Origin"
                # Standalone widget visitor requests must never reflect credentials
                if "access-control-allow-credentials" in res_headers:
                    del res_headers["access-control-allow-credentials"]
            await send(message)

        await self.app(scope, receive, widget_send_wrapper)


dashboard_origins = get_dashboard_cors_origins()

# Configure Decoupled CORS: explicit dashboard origins with credentials,
# and separate credential-free origin verification for standalone widget visitors
app.add_middleware(
    DecoupledCORSMiddleware,
    allow_origins=dashboard_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(tenants.router)
app.include_router(databases.router)
app.include_router(api_keys.router)
app.include_router(chatbot_config.router)
app.include_router(documents.router)
app.include_router(query.router)
app.include_router(chat.router)
app.include_router(analytics.router)
app.include_router(analytics.core_router)
app.include_router(connections.router)
app.include_router(insights.router)
app.include_router(files.router)
app.include_router(file_insights.router)
app.include_router(widget.router)
app.include_router(erd.router)


@app.get("/")
def read_root():
    return {"message": "Welcome to DataSpeakAI Platform API"}


@app.get("/widget.js")
def get_widget_script():
    """
    Serves the compiled standalone widget bundle with strict caching and security headers.
    """
    candidates = [
        os.path.join(backend_dir, "..", "dist", "widget.js"),
        os.path.join(backend_dir, "..", "public", "widget.js"),
        os.path.join(backend_dir, "static", "widget.js"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return FileResponse(
                path,
                media_type="application/javascript",
                headers={
                    "Content-Type": "application/javascript",
                    "X-Content-Type-Options": "nosniff",
                    "Cache-Control": "public, max-age=300",
                    "Access-Control-Allow-Origin": "*"
                }
            )
    return JSONResponse(
        status_code=404,
        content={"detail": "Widget bundle not built yet. Run 'npm run build:widget' first."}
    )


@app.get("/embed/{public_key}", response_class=HTMLResponse)
def get_widget_embed_root(public_key: str, request: Request, db: Session = Depends(get_db)):
    """
    Direct root fallback iframe embed page.
    """
    return widget.get_widget_embed_page(public_key, request, db)


@app.get("/api/system/llm-metrics")
def get_system_llm_metrics(current_user: models.User = Depends(get_current_admin_user)):
    """
    Returns aggregated LLM gateway telemetry and key health metrics (Admin only).
    """
    from services.llm_metrics import llm_metrics
    return llm_metrics.get_summary()

