# DataSpeakAI v4 - Setup Guide

This guide will help you set up and run DataSpeakAI on your local machine.

## 📋 Prerequisites
- **Node.js** (v18 or higher)
- **Python** (v3.9 or higher)

---

## 🚀 Installation

### 1. Backend Setup (FastAPI)
Navigate to the `backend` directory:
```bash
cd backend
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Frontend Setup (React + Vite)
Navigate to the project root:
```bash
npm install
```

---

## 🏃 Running the Application

### Terminal 1: Start Backend
```bash
cd backend
# Ensure venv is activated
python -m uvicorn main:app --reload --port 8000
```

### Terminal 2: Start Frontend
```bash
npm run dev
```

The app will be available at **http://localhost:5173**.

---

## 🛠️ Key Features in v4
- **Knowledge Base (RAG)**: Upload PDFs and chat with your documents using local embeddings (FAISS).
- **Database Explorer**: Connect to live **PostgreSQL** (e.g., Neon.tech) or **MySQL** databases and browse tables/data in real-time.
- **Tenant Isolation**: Secure multi-tenant architecture.
