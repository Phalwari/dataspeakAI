from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import models
from database import engine
from routers import users, tenants, databases, api_keys, chatbot_config, documents, analytics
from dotenv import load_dotenv
import os

load_dotenv()

# Create all tables in the database
models.Base.metadata.create_all(bind=engine)

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
app.include_router(analytics.router)


@app.get("/")
def read_root():
    return {"message": "Welcome to the SaaS Chatbot API"}
