
  ## Running the code

  Run `npm i` to install the dependencies.

  Run `npm run dev` to start the development server.
  
# DataSpeakAI Setup Guide

DataSpeakAI is an AI-powered business intelligence platform that allows you to connect databases and upload documents for semantic search and natural language querying.

## 📋 Prerequisites

Before you begin, ensure you have the following installed on your machine:

- **Node.js** (v18 or higher)
- **Python** (v3.9 or higher)
- **Git** (optional, for cloning)

---

## 🚀 Getting Started

### 1. Extract the Project
If you received the project as a `.zip` file, extract it to a folder of your choice.

### 2. Backend Setup (FastAPI)
Navigate to the `backend` directory and set up the Python environment:

```bash
cd backend
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Frontend Setup (Vite + React)
Navigate back to the project root and install the Node dependencies:

```bash
# From the project root
npm install
```

### 4. Configuration
Ensure the `.env` file in the project root points to your backend:
```env
VITE_API_BASE_URL=http://localhost:8000
```

---

## 🏃 Running the Application

You will need two terminal windows open.

### Terminal 1: Start the Backend
```bash
cd backend
# Ensure venv is activated
python -m uvicorn main:app --reload --port 8000
```

### Terminal 2: Start the Frontend
```bash
# From the project root
npm run dev
```

The application will be available at [http://localhost:5173](http://localhost:5173).

---

## 🛠️ Features

- **Databases**: Connect and manage SQL/NoSQL databases.
- **Knowledge Base**: Upload PDF/TXT documents for AI semantic search.
- **Analytics**: Visualize your data trends.
- **AI Assistant**: Query your data using natural language.

## 📝 Notes
- The first time you upload a document, the backend will download the `all-MiniLM-L6-v2` embedding model (approx. 80MB).
- Vector indices are stored locally in the `backend/vector_store/` directory.
