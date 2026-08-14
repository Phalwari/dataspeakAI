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
from routers import users, tenants, databases, api_keys, chatbot_config, documents, query, analytics, chat
from dotenv import load_dotenv

load_dotenv()

# Create all tables in the database
models.Base.metadata.create_all(bind=engine)

# Automatically ensure default Superadmin user and tenant exist for fresh environments
try:
    from scripts.seed_admin import seed_superadmin
    seed_superadmin()
except Exception as e:
    print(f"[STARTUP] Superadmin seed note: {e}")

app = FastAPI(title="SaaS Chatbot Platform API")

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
app.include_router(analytics.router)
app.include_router(chat.router)


@app.get("/")
def read_root():
    return {"message": "Welcome to the SaaS Chatbot API"}
