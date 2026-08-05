# DataSpeakAI v5 - Setup & Deployment Guide

Welcome to **DataSpeakAI**, a professional AI-driven SaaS platform for business data intelligence. This guide covers how to set up the application on a fresh machine.

## 📋 Prerequisites
Before starting, ensure you have the following installed:
- **Node.js** (v18.0 or higher)
- **Python** (v3.9 or higher)
- **Git** (optional, for version control)

---

## 🚀 Installation Steps

### 1. Backend Setup (FastAPI)
1. Navigate to the `backend` directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   # Windows:
   python -m venv venv
   .\venv\Scripts\activate

   # Mac/Linux:
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configuration:
   - Create a `.env` file in the `backend` folder.
   - Add your database URL and secret keys (refer to `.env.example`).

### 2. Frontend Setup (React + Vite)
1. Navigate to the project root:
   ```bash
   cd ..
   ```
2. Install Node dependencies:
   ```bash
   npm install
   ```

---

## 🏃 Running the Application

To run DataSpeakAI, you need to start both the backend and frontend servers.

### Terminal 1: Backend Server
```bash
cd backend
# Activate venv if not already active
python -m uvicorn main:app --reload --port 8000
```

### Terminal 2: Frontend Server
```bash
npm run dev
```

The application will be available at **http://localhost:5173**.

---

## 🛠️ Project Features
- **Module 1-20 Implementation**: Full support for all defined SaaS modules.
- **AI Knowledge Base**: RAG integration for document chatting.
- **Database Explorer**: Connect to live PostgreSQL/MySQL databases.
- **Chatbot Widget**: Embeddable widget with customizable styling.
- **Multi-Tenant Architecture**: Secure tenant isolation and RBAC.

## 📁 File Structure (Core)
- `/src`: React frontend source code.
- `/backend`: FastAPI backend logic and models.
- `/backend/models.py`: Database schema definitions.
- `/backend/vector_store`: AI embeddings storage.

---
© 2026 DataSpeakAI. Professional AI Intelligence.
