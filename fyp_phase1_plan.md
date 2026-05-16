# FYP Phase 1 Implementation Plan (30% MVP)

To implement 30% of your total modules (6 out of 20), we need to select the ones that are **easiest to build**, **completely free** (no paid APIs), and **form a logical, working MVP** that you can show to your professors.

We will avoid Stripe (Billing) and complex Multi-Agent LLM generation for this first phase to keep things simple, while ensuring we still have a "wow-factor" AI feature.

Here are the **Top 6 Modules** I recommend building first, utilizing your exact tech stack (React + FastAPI + MongoDB/SQL + LangChain):

### 1. Module 1: User Authentication & Identity Management
*   **Why it's easy:** FastAPI has built-in support for OAuth2 and JWT tokens. You already have the React UI for Login/Signup.
*   **Tech Stack:** React (UI) + FastAPI (JWT Auth) + MongoDB/SQL (User Table).
*   **Cost:** 100% Free.

### 2. Module 2: Tenant (Business) Onboarding & Profile Management
*   **Why it's easy:** This is standard CRUD (Create, Read, Update, Delete). It's just saving business details (name, industry) into your database.
*   **Tech Stack:** React (Settings UI) + FastAPI + Database.
*   **Cost:** 100% Free.

### 3. Module 4: Database Connection & Credential Management
*   **Why it's easy:** You just need to build a form where users paste their PostgreSQL/MongoDB connection strings, and your FastAPI backend tests if it can connect.
*   **Tech Stack:** React (Databases UI) + FastAPI (SQLAlchemy/PyMongo to test connection).
*   **Cost:** 100% Free.

### 4. Module 6: API Key Generation & Lifecycle Management
*   **Why it's easy:** Generating an API key is as simple as generating a random UUID string in Python and saving it to the database.
*   **Tech Stack:** FastAPI (Python `uuid` library) + React (API Keys UI).
*   **Cost:** 100% Free.

### 5. Module 7: Chatbot Widget SDK & Frontend Integration
*   **Why it's easy:** It's just building the chat UI component (which you already have designs for). For this phase, you can just make the backend return a mocked "Hello, I am connected to your database!" response, or wire it up directly to Module 17. It gives your FYP a visual "wow" factor.
*   **Tech Stack:** React.
*   **Cost:** 100% Free.

### 6. Module 17: Knowledge Base & RAG Document Search (The AI Wow-Factor)
*   **Why it's easy:** Instead of jumping straight into the extremely difficult text-to-SQL generation, RAG (Retrieval-Augmented Generation) is much more straightforward to set up and very impressive. It allows users to upload PDFs and chat with them.
*   **Tech Stack:** 
    *   **Qdrant Vector Database**: Run locally via Docker (Free).
    *   **LangChain**: To process PDFs and create embeddings.
    *   **Embeddings**: Use open-source HuggingFace embeddings via LangChain (Runs locally, no OpenAI API costs).
*   **Cost:** 100% Free.

---

### What to avoid right now:
*   **Module 3 & 20 (Billing & Stripe):** Time-consuming to configure webhooks, wait until the end.
*   **Module 12, 13, 14 (AI Query Generation / Text-to-SQL):** Generating safe SQL from text is the hardest part of your project. Leave it for Phase 2 once the foundation is solid.
