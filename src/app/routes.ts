import { createBrowserRouter } from "react-router";
import { LandingPage } from "./pages/LandingPage";
import { LoginPage } from "./pages/LoginPage";
import { SignupPage } from "./pages/SignupPage";
import { ForgotPasswordPage } from "./pages/ForgotPasswordPage";
import { EmailVerificationPage } from "./pages/EmailVerificationPage";
import { DashboardLayout } from "./components/DashboardLayout";
import { DashboardOverview } from "./pages/dashboard/DashboardOverview";
import { DatabasesPage } from "./pages/dashboard/DatabasesPage";
import { KnowledgeBasePage } from "./pages/dashboard/KnowledgeBasePage";
import { UploadDocumentsPage } from "./pages/dashboard/UploadDocumentsPage";
import { AnalyticsPage } from "./pages/dashboard/AnalyticsPage";
import { AIInsightsPage } from "./pages/dashboard/AIInsightsPage";
import { ApiKeysPage } from "./pages/dashboard/ApiKeysPage";
import { ChatbotWidgetPage } from "./pages/dashboard/ChatbotWidgetPage";
import { ChatPage } from "./pages/dashboard/ChatPage";
import { UsagePage } from "./pages/dashboard/UsagePage";
import { LogsPage } from "./pages/dashboard/LogsPage";
import { SettingsPage } from "./pages/dashboard/SettingsPage";
import { AdminPanel } from "./pages/admin/AdminPanel";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: LandingPage,
  },
  {
    path: "/login",
    Component: LoginPage,
  },
  {
    path: "/signup",
    Component: SignupPage,
  },
  {
    path: "/forgot-password",
    Component: ForgotPasswordPage,
  },
  {
    path: "/verify-email",
    Component: EmailVerificationPage,
  },
  {
    path: "/dashboard",
    Component: DashboardLayout,
    children: [
      {
        index: true,
        Component: DashboardOverview,
      },
      {
        path: "chat",
        Component: ChatPage,
      },
      {
        path: "databases",
        Component: DatabasesPage,
      },
      {
        path: "knowledge-base",
        Component: KnowledgeBasePage,
      },
      {
        path: "upload-documents",
        Component: UploadDocumentsPage,
      },
      {
        path: "analytics",
        Component: AnalyticsPage,
      },
      {
        path: "ai-insights",
        Component: AIInsightsPage,
      },
      {
        path: "api-keys",
        Component: ApiKeysPage,
      },
      {
        path: "chatbot",
        Component: ChatbotWidgetPage,
      },
      {
        path: "usage",
        Component: UsagePage,
      },
      {
        path: "logs",
        Component: LogsPage,
      },
      {
        path: "settings",
        Component: SettingsPage,
      },
    ],
  },
  {
    path: "/admin",
    Component: AdminPanel,
  },
]);

