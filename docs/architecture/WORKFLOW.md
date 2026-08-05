# DataSpeakAI Development & Deployment Workflow

> [!IMPORTANT]
> **AI ASSISTANT INSTRUCTION:** Before starting any work on this project, the AI MUST read this file to understand the specific architectural constraints (Lazy Loading, Render Free Tier, PYTHONPATH) of DataSpeakAI.

## 🤖 0. AI Synchronization Protocol
When starting a new session, the AI assistant should:
1.  Read `WORKFLOW.md` and `render.yaml`.
2.  Acknowledge that this is a **Production-Live** repository.
3.  Ensure all new backend imports are **Lazy-Loaded** within function scopes to prevent OOM (Out Of Memory) crashes on Render.

This document outlines the standard operating procedures for developing, testing, and deploying the DataSpeakAI platform.

## 🚀 1. Local Development Environment

### Backend (FastAPI)
- **Directory:** `/backend`
- **Start Command:** `uvicorn main:app --reload`
- **Environment:** Ensure `.env` is populated with keys for Auth, Email, and AI.
- **Port:** Default is `http://localhost:8000`

### Frontend (React + Vite)
- **Directory:** Project Root
- **Start Command:** `npm run dev`
- **API Connection:** Ensure `.env.local` has `VITE_API_BASE_URL=http://localhost:8000`
- **Port:** Default is `http://localhost:5173`

---

## 🛠️ 2. Production Constraints (Render Free Tier)

To prevent **Out of Memory (OOM)** errors on Render's Free Tier:
1. **Lazy Loading:** All heavy AI libraries (LangChain, FAISS, PyPDF, HuggingFace) MUST be imported inside function scopes, not at the top of the file.
2. **PYTHONPATH:** The `render.yaml` must always set `PYTHONPATH` to `backend` to ensure module resolution works correctly.
3. **Implicit Packages:** Ensure every folder in the backend (like `routers/`) has an `__init__.py` file.

---

## 🌐 3. The Deployment Process

Follow these steps for every new feature or fix:

### Step A: Local Verification
Test the feature locally to ensure no regressions.
```powershell
# Verify backend starts
cd backend
uvicorn main:app
```

### Step B: The "Power Push"
Push to the `main` branch to trigger the CI/CD pipeline.
```powershell
git add .
git commit -m "feat: description of your change"
git push origin main
```

### Step C: Monitor the Cloud
1. **Render (Backend):** Check [Render Dashboard](https://dashboard.render.com) for "Live" status and "Application startup complete" in logs.
2. **Vercel (Frontend):** Check [Vercel Dashboard](https://vercel.com) to ensure the build finishes.

---

## 🔐 4. Environment Variable Management

| Variable | Location | Purpose |
| :--- | :--- | :--- |
| `SECRET_KEY` | Render Dashboard | Security for JWT Tokens |
| `VITE_API_BASE_URL` | Vercel Dashboard | Points frontend to Render backend |
| `DATABASE_URL` | Render Dashboard | PostgreSQL connection string |
| `RESEND_API_KEY` | Render Dashboard | Email delivery |

**CRITICAL:** When adding a new variable, you must add it to the Render/Vercel dashboards manually.

---

## 📂 5. Repository Structure Reference
- `/backend`: FastAPI source code.
- `/backend/routers`: API endpoints (Modules).
- `/src`: React frontend source code.
- `render.yaml`: Render blueprint configuration.
- `vercel.json`: Vercel routing for SPAs.
