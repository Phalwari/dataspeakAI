import os
import json
import re
import sys

BASE_DIR = r"d:\dataspeak"

paths_to_check = [
    # 3.1 Root & Docs
    os.path.join(BASE_DIR, ".agents"),
    os.path.join(BASE_DIR, "docs"),
    os.path.join(BASE_DIR, "docs", "architecture", "TECHNICAL_ANALYSIS_AND_ROADMAP.md"),
    os.path.join(BASE_DIR, "docs", "architecture", "WORKFLOW.md"),
    os.path.join(BASE_DIR, "docs", "architecture", "activity_diagrams.md"),
    os.path.join(BASE_DIR, "docs", "architecture", "database_connection_workflow.md"),
    os.path.join(BASE_DIR, "docs", "architecture", "fyp_phase1_plan.md"),
    os.path.join(BASE_DIR, "docs", "database", "Full_Project_Schemas.sql"),
    os.path.join(BASE_DIR, "docs", "database", "Database_ERD.md"),
    os.path.join(BASE_DIR, "docs", "database", "DataSpeakAI_Complete_EERD.md"),
    os.path.join(BASE_DIR, "docs", "database", "dataspeakai_complete_eerd_visual_1778525676843.png"),
    os.path.join(BASE_DIR, "docs", "setup", "SETUP_GUIDE.md"),
    os.path.join(BASE_DIR, "docs", "setup", "SETUP_GUIDE_v4.md"),
    os.path.join(BASE_DIR, "docs", "setup", "setup_guide_v5.md"),
    os.path.join(BASE_DIR, "docs", "setup", "Guidelines.md"),
    os.path.join(BASE_DIR, "docs", "setup", "instructions.txt"),
    os.path.join(BASE_DIR, "docs", "reports", "ATTRIBUTIONS.md"),
    os.path.join(BASE_DIR, "docs", "reports", "Ingestion_Summary.md"),
    os.path.join(BASE_DIR, "docs", "reports", "implementation_planmodule17"),
    os.path.join(BASE_DIR, "docs", "reports", "mockup_analysis.md"),
    os.path.join(BASE_DIR, "docs", "reports", "project_implementation_report_30.md"),
    os.path.join(BASE_DIR, "docs", "reports", "walkthroughmodule17"),
    os.path.join(BASE_DIR, "docs", "sessions"),
    os.path.join(BASE_DIR, "docs", "templates", "AI_TASK_TEMPLATE.md"),
    os.path.join(BASE_DIR, "src"),
    os.path.join(BASE_DIR, "backend"),
    os.path.join(BASE_DIR, "package.json"),
    os.path.join(BASE_DIR, "vite.config.ts"),
    os.path.join(BASE_DIR, "postcss.config.mjs"),
    os.path.join(BASE_DIR, "index.html"),
    os.path.join(BASE_DIR, "proxy.js"),
    os.path.join(BASE_DIR, "render.yaml"),
    os.path.join(BASE_DIR, "vercel.json"),
    os.path.join(BASE_DIR, ".env.example"),
    os.path.join(BASE_DIR, "README.md"),
    os.path.join(BASE_DIR, "AGENTS.md"),
    os.path.join(BASE_DIR, "CHANGELOG.md"),

    # 3.2 Frontend
    os.path.join(BASE_DIR, "src", "main.tsx"),
    os.path.join(BASE_DIR, "src", "styles", "index.css"),
    os.path.join(BASE_DIR, "src", "styles", "tailwind.css"),
    os.path.join(BASE_DIR, "src", "styles", "theme.css"),
    os.path.join(BASE_DIR, "src", "styles", "fonts.css"),
    os.path.join(BASE_DIR, "src", "app", "App.tsx"),
    os.path.join(BASE_DIR, "src", "app", "routes.ts"),
    os.path.join(BASE_DIR, "src", "app", "config", "api.ts"),
    os.path.join(BASE_DIR, "src", "app", "components", "DashboardLayout.tsx"),
    os.path.join(BASE_DIR, "src", "app", "components", "ui"),
    os.path.join(BASE_DIR, "src", "app", "components", "figma"),
    os.path.join(BASE_DIR, "src", "app", "pages", "LandingPage.tsx"),
    os.path.join(BASE_DIR, "src", "app", "pages", "LoginPage.tsx"),
    os.path.join(BASE_DIR, "src", "app", "pages", "SignupPage.tsx"),
    os.path.join(BASE_DIR, "src", "app", "pages", "ForgotPasswordPage.tsx"),
    os.path.join(BASE_DIR, "src", "app", "pages", "EmailVerificationPage.tsx"),
    os.path.join(BASE_DIR, "src", "app", "pages", "admin", "AdminPanel.tsx"),
    os.path.join(BASE_DIR, "src", "app", "pages", "dashboard", "DashboardOverview.tsx"),
    os.path.join(BASE_DIR, "src", "app", "pages", "dashboard", "DatabasesPage.tsx"),
    os.path.join(BASE_DIR, "src", "app", "pages", "dashboard", "KnowledgeBasePage.tsx"),
    os.path.join(BASE_DIR, "src", "app", "pages", "dashboard", "UploadDocumentsPage.tsx"),
    os.path.join(BASE_DIR, "src", "app", "pages", "dashboard", "AnalyticsPage.tsx"),
    os.path.join(BASE_DIR, "src", "app", "pages", "dashboard", "AIInsightsPage.tsx"),
    os.path.join(BASE_DIR, "src", "app", "pages", "dashboard", "ApiKeysPage.tsx"),
    os.path.join(BASE_DIR, "src", "app", "pages", "dashboard", "ChatbotWidgetPage.tsx"),
    os.path.join(BASE_DIR, "src", "app", "pages", "dashboard", "UsagePage.tsx"),
    os.path.join(BASE_DIR, "src", "app", "pages", "dashboard", "LogsPage.tsx"),
    os.path.join(BASE_DIR, "src", "app", "pages", "dashboard", "SettingsPage.tsx"),

    # 3.3 Backend
    os.path.join(BASE_DIR, "backend", "main.py"),
    os.path.join(BASE_DIR, "backend", "database.py"),
    os.path.join(BASE_DIR, "backend", "models.py"),
    os.path.join(BASE_DIR, "backend", "schemas.py"),
    os.path.join(BASE_DIR, "backend", "auth.py"),
    os.path.join(BASE_DIR, "backend", "dependencies.py"),
    os.path.join(BASE_DIR, "backend", "requirements.txt"),
    os.path.join(BASE_DIR, "backend", "proxy.js"),
    os.path.join(BASE_DIR, "backend", "routers", "users.py"),
    os.path.join(BASE_DIR, "backend", "routers", "tenants.py"),
    os.path.join(BASE_DIR, "backend", "routers", "databases.py"),
    os.path.join(BASE_DIR, "backend", "routers", "api_keys.py"),
    os.path.join(BASE_DIR, "backend", "routers", "chatbot_config.py"),
    os.path.join(BASE_DIR, "backend", "routers", "documents.py")
]

results = []
missing = []
for p in paths_to_check:
    exists = os.path.exists(p)
    results.append((p, exists))
    if not exists:
        missing.append(p)

print(f"Total paths checked: {len(paths_to_check)}")
print(f"Existing paths: {len(paths_to_check) - len(missing)}")
print(f"Missing paths: {len(missing)}")
if missing:
    print("MISSING PATHS:")
    for m in missing:
        print("  -", m)
else:
    print("ALL PATHS EXIST ON DISK!")
