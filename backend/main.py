import sys
import os

# Ensure backend directory is in sys.path when imported from root or elsewhere
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import models
from database import engine
from routers import (
    users, tenants, databases, api_keys, chatbot_config, documents,
    query, chat, analytics, connections, insights, files, file_insights
)
from dotenv import load_dotenv

load_dotenv()

# Check secret key
SECRET_KEY = os.getenv("SECRET_KEY", "dataspeakai-default-encryption-secret-key-32b")
if not SECRET_KEY:
    print("[WARNING] SECRET_KEY environment variable not set. Using fallback for development.")

# Create all tables in the database
models.Base.metadata.create_all(bind=engine)

# Automatically sync newly added model columns for SQLite / PostgreSQL
try:
    from services.db_migration import run_schema_migrations
    run_schema_migrations(engine)
except Exception as e:
    print(f"[MIGRATION] Startup schema sync note: {e}")

# Automatically ensure default Superadmin user and tenant exist for fresh environments
try:
    from scripts.seed_admin import seed_superadmin
    seed_superadmin()
except Exception as e:
    print(f"[STARTUP] Superadmin seed note: {e}")

app = FastAPI(title="DataSpeakAI Platform API")

# Configure CORS so the React frontend can communicate with the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for ngrok/remote access
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


@app.get("/")
def read_root():
    return {"message": "Welcome to DataSpeakAI Platform API"}
