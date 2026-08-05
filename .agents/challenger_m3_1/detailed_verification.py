import os
import json
import re

BASE_DIR = r"d:\dataspeak"
AGENTS_MD_PATH = os.path.join(BASE_DIR, "AGENTS.md")

def log(msg):
    print(msg)

log("=== EMPIRICAL VERIFICATION SUITE FOR AGENTS.MD ===")

# 1. Check AGENTS.md existence & size
if os.path.exists(AGENTS_MD_PATH):
    size = os.path.getsize(AGENTS_MD_PATH)
    log(f"[CHECK 1] AGENTS.md exists at root. Size: {size} bytes. (PASS)")
else:
    log("[CHECK 1] AGENTS.md MISSING at root! (FAIL)")

# 2. Check Package Versions in package.json vs AGENTS.md
package_json_path = os.path.join(BASE_DIR, "package.json")
with open(package_json_path, "r", encoding="utf-8") as f:
    pkg = json.load(f)

deps = pkg.get("dependencies", {})
dev_deps = pkg.get("devDependencies", {})
peer_deps = pkg.get("peerDependencies", {})
all_deps = {**deps, **dev_deps, **peer_deps}

expected_pkg_versions = {
    "react": "18.3.1",
    "vite": "6.3.5",
    "react-router": "^7.13.0",
    "@tailwindcss/vite": "4.1.12",
    "tailwindcss": "4.1.12",
    "@emotion/react": "11.14.0",
    "@emotion/styled": "11.14.1",
    "@mui/material": "7.3.5",
    "@mui/icons-material": "7.3.5",
    "motion": "12.23.24",
    "clsx": "2.1.1",
    "tailwind-merge": "3.2.0",
    "class-variance-authority": "0.7.1",
    "tw-animate-css": "1.3.8",
    "recharts": "2.15.2",
    "sonner": "2.0.3",
    "vaul": "1.1.2",
    "cmdk": "1.1.1",
    "lucide-react": "0.487.0",
    "embla-carousel-react": "8.6.0",
    "react-hook-form": "7.55.0",
    "react-dnd": "16.0.1",
    "react-resizable-panels": "2.1.7"
}

pkg_mismatches = []
for pkg_name, expected_ver in expected_pkg_versions.items():
    actual_ver = all_deps.get(pkg_name)
    if actual_ver != expected_ver:
        pkg_mismatches.append((pkg_name, expected_ver, actual_ver))

if pkg_mismatches:
    log(f"[CHECK 2] package.json version mismatches: {pkg_mismatches} (FAIL)")
else:
    log("[CHECK 2] package.json versions match AGENTS.md specifications perfectly. (PASS)")

# 3. Check requirements.txt vs AGENTS.md
req_path = os.path.join(BASE_DIR, "backend", "requirements.txt")
with open(req_path, "r", encoding="utf-8") as f:
    req_lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

expected_reqs = [
    "fastapi", "uvicorn", "sqlalchemy", "pydantic[email]", "passlib[bcrypt]",
    "PyJWT", "psycopg2-binary", "pymysql", "faiss-cpu", "langchain-huggingface",
    "resend", "pdfplumber", "pymupdf"
]

req_missing = [r for r in expected_reqs if not any(r.lower() in line.lower() for line in req_lines)]
if req_missing:
    log(f"[CHECK 3] backend/requirements.txt missing expected libraries: {req_missing} (FAIL)")
else:
    log("[CHECK 3] backend/requirements.txt contains all specified backend libraries. (PASS)")

# 4. Check Backend Models count & ORM classes in backend/models.py
models_path = os.path.join(BASE_DIR, "backend", "models.py")
with open(models_path, "r", encoding="utf-8") as f:
    models_content = f.read()

model_classes = re.findall(r"class\s+(\w+)\(Base\):", models_content)
expected_models = [
    "Tenant", "User", "UserDatabaseAccess", "TenantInvite",
    "DatabaseConnection", "ApiKey", "ChatbotConfig", "Document",
    "DocumentChunk", "PasswordResetOTP"
]

if set(model_classes) == set(expected_models) and len(model_classes) == 10:
    log(f"[CHECK 4] backend/models.py contains exactly 10 models: {model_classes} (PASS)")
else:
    log(f"[CHECK 4] backend/models.py model mismatch! Found: {model_classes}, Expected: {expected_models} (FAIL)")

# 5. Check SQL Schema table count in docs/database/Full_Project_Schemas.sql
sql_path = os.path.join(BASE_DIR, "docs", "database", "Full_Project_Schemas.sql")
with open(sql_path, "r", encoding="utf-8") as f:
    sql_content = f.read()

tables_found = re.findall(r"CREATE\s+TABLE\s+(\w+)", sql_content, re.IGNORECASE)
if len(tables_found) == 35:
    log(f"[CHECK 5] Full_Project_Schemas.sql contains exactly 35 tables (PASS)")
else:
    log(f"[CHECK 5] Full_Project_Schemas.sql table count mismatch! Count: {len(tables_found)} (FAIL)")

# 6. Verify Router files in backend/routers/
router_dir = os.path.join(BASE_DIR, "backend", "routers")
expected_routers = ["users.py", "tenants.py", "databases.py", "api_keys.py", "chatbot_config.py", "documents.py"]
actual_routers = os.listdir(router_dir) if os.path.exists(router_dir) else []
missing_routers = set(expected_routers) - set(actual_routers)
if not missing_routers:
    log(f"[CHECK 6] backend/routers/ contains all 6 documented router files (PASS)")
else:
    log(f"[CHECK 6] backend/routers/ missing: {missing_routers} (FAIL)")

# 7. Check Frontend Routes in src/app/routes.ts
routes_path = os.path.join(BASE_DIR, "src", "app", "routes.ts")
if os.path.exists(routes_path):
    log("[CHECK 7] src/app/routes.ts exists. (PASS)")
else:
    log("[CHECK 7] src/app/routes.ts MISSING! (FAIL)")

# 8. Document Tree Discrepancy Analysis
documented_tree_items = {
    "docs/architecture/TECHNICAL_ANALYSIS_AND_ROADMAP.md": os.path.exists(os.path.join(BASE_DIR, "docs", "architecture", "TECHNICAL_ANALYSIS_AND_ROADMAP.md")),
    "docs/architecture/WORKFLOW.md": os.path.exists(os.path.join(BASE_DIR, "docs", "architecture", "WORKFLOW.md")),
    "docs/architecture/activity_diagrams.md": os.path.exists(os.path.join(BASE_DIR, "docs", "architecture", "activity_diagrams.md")),
    "docs/architecture/database_connection_workflow.md": os.path.exists(os.path.join(BASE_DIR, "docs", "architecture", "database_connection_workflow.md")),
    "docs/architecture/fyp_phase1_plan.md": os.path.exists(os.path.join(BASE_DIR, "docs", "architecture", "fyp_phase1_plan.md")),
    "docs/database/Full_Project_Schemas.sql": os.path.exists(os.path.join(BASE_DIR, "docs", "database", "Full_Project_Schemas.sql")),
    "docs/database/Database_ERD.md": os.path.exists(os.path.join(BASE_DIR, "docs", "database", "Database_ERD.md")),
    "docs/database/DataSpeakAI_Complete_EERD.md": os.path.exists(os.path.join(BASE_DIR, "docs", "database", "DataSpeakAI_Complete_EERD.md")),
    "docs/database/dataspeakai_complete_eerd_visual_1778525676843.png": os.path.exists(os.path.join(BASE_DIR, "docs", "database", "dataspeakai_complete_eerd_visual_1778525676843.png")),
    "docs/setup/SETUP_GUIDE.md": os.path.exists(os.path.join(BASE_DIR, "docs", "setup", "SETUP_GUIDE.md")),
    "docs/setup/SETUP_GUIDE_v4.md": os.path.exists(os.path.join(BASE_DIR, "docs", "setup", "SETUP_GUIDE_v4.md")),
    "docs/setup/setup_guide_v5.md": os.path.exists(os.path.join(BASE_DIR, "docs", "setup", "setup_guide_v5.md")),
    "docs/setup/Guidelines.md": os.path.exists(os.path.join(BASE_DIR, "docs", "setup", "Guidelines.md")),
    "docs/setup/instructions.txt": os.path.exists(os.path.join(BASE_DIR, "docs", "setup", "instructions.txt")),
    "docs/reports/ATTRIBUTIONS.md": os.path.exists(os.path.join(BASE_DIR, "docs", "reports", "ATTRIBUTIONS.md")),
    "docs/reports/Ingestion_Summary.md": os.path.exists(os.path.join(BASE_DIR, "docs", "reports", "Ingestion_Summary.md")),
    "docs/reports/implementation_planmodule17": os.path.exists(os.path.join(BASE_DIR, "docs", "reports", "implementation_planmodule17")),
    "docs/reports/mockup_analysis.md": os.path.exists(os.path.join(BASE_DIR, "docs", "reports", "mockup_analysis.md")),
    "docs/reports/project_implementation_report_30.md": os.path.exists(os.path.join(BASE_DIR, "docs", "reports", "project_implementation_report_30.md")),
    "docs/reports/walkthroughmodule17": os.path.exists(os.path.join(BASE_DIR, "docs", "reports", "walkthroughmodule17")),
    "docs/sessions/": os.path.exists(os.path.join(BASE_DIR, "docs", "sessions")),
    "docs/templates/AI_TASK_TEMPLATE.md": os.path.exists(os.path.join(BASE_DIR, "docs", "templates", "AI_TASK_TEMPLATE.md")),
    "CHANGELOG.md": os.path.exists(os.path.join(BASE_DIR, "CHANGELOG.md")),
    "backend/proxy.js": os.path.exists(os.path.join(BASE_DIR, "backend", "proxy.js")),
    "proxy.js (root)": os.path.exists(os.path.join(BASE_DIR, "proxy.js")),
}

log("\n=== DISCREPANCY ANALYSIS ===")
for path_str, exists in documented_tree_items.items():
    status = "EXISTS" if exists else "MISSING / INCORRECT PATH"
    log(f"  {path_str}: {status}")

