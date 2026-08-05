import os

BASE_DIR = r"d:\dataspeak"
frontend_paths = [
    "src/main.tsx",
    "src/styles/index.css",
    "src/styles/tailwind.css",
    "src/styles/theme.css",
    "src/styles/fonts.css",
    "src/app/App.tsx",
    "src/app/routes.ts",
    "src/app/config/api.ts",
    "src/app/components/DashboardLayout.tsx",
    "src/app/components/ui",
    "src/app/components/figma",
    "src/app/pages/LandingPage.tsx",
    "src/app/pages/LoginPage.tsx",
    "src/app/pages/SignupPage.tsx",
    "src/app/pages/ForgotPasswordPage.tsx",
    "src/app/pages/EmailVerificationPage.tsx",
    "src/app/pages/admin/AdminPanel.tsx",
    "src/app/pages/dashboard/DashboardOverview.tsx",
    "src/app/pages/dashboard/DatabasesPage.tsx",
    "src/app/pages/dashboard/KnowledgeBasePage.tsx",
    "src/app/pages/dashboard/UploadDocumentsPage.tsx",
    "src/app/pages/dashboard/AnalyticsPage.tsx",
    "src/app/pages/dashboard/AIInsightsPage.tsx",
    "src/app/pages/dashboard/ApiKeysPage.tsx",
    "src/app/pages/dashboard/ChatbotWidgetPage.tsx",
    "src/app/pages/dashboard/UsagePage.tsx",
    "src/app/pages/dashboard/LogsPage.tsx",
    "src/app/pages/dashboard/SettingsPage.tsx"
]

for p in frontend_paths:
    full_p = os.path.join(BASE_DIR, p)
    exists = os.path.exists(full_p)
    print(f"{p}: {'EXISTS' if exists else 'MISSING'}")
