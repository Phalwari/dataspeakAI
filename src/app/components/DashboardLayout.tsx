import { Outlet, NavLink, useNavigate } from "react-router";
import { useState, useEffect } from "react";
import { API_BASE_URL } from "../config/api";
import {
  LayoutDashboard,
  Database,
  Key,
  MessageSquare,
  BarChart3,
  FileText,
  Settings,
  Bell,
  ChevronDown,
  BookOpen,
  Lightbulb,
  Activity,
  Building2,
  MessageSquareCode,
} from "lucide-react";
import { Button } from "./ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "./ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "./ui/avatar";

const navigation = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "AI Assistant (Chat)", href: "/dashboard/chat", icon: MessageSquare },
  { name: "Databases", href: "/dashboard/databases", icon: Database },
  { name: "Knowledge Base", href: "/dashboard/knowledge-base", icon: BookOpen },
  { name: "Analytics & Visualization", href: "/dashboard/analytics", icon: BarChart3 },
  { name: "AI Insights", href: "/dashboard/ai-insights", icon: Lightbulb },
  { name: "API Keys", href: "/dashboard/api-keys", icon: Key },
  { name: "Chatbot Widget", href: "/dashboard/chatbot", icon: MessageSquareCode },
  { name: "Usage", href: "/dashboard/usage", icon: Activity },
  { name: "Logs", href: "/dashboard/logs", icon: FileText },
  { name: "Settings", href: "/dashboard/settings", icon: Settings },
];

export function DashboardLayout() {
  const navigate = useNavigate();
  const [userName, setUserName] = useState("Loading...");
  const [organizationName, setOrganizationName] = useState("Loading...");

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const token = localStorage.getItem("token");
        if (!token) {
          navigate("/login");
          return;
        }

        // Fetch User
        const userRes = await fetch(`${API_BASE_URL}/api/auth/me`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        
        if (!userRes.ok) {
          localStorage.removeItem("token");
          navigate("/login");
          return;
        }

        const userData = await userRes.json();
        setUserName(userData.full_name || userData.email);

        // Fetch Tenant
        const tenantRes = await fetch(`${API_BASE_URL}/api/tenant/current`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (tenantRes.ok) {
          const tenantData = await tenantRes.json();
          setOrganizationName(tenantData.name);
        }
      } catch (err) {
        console.error("Failed to fetch profile", err);
      }
    };
    fetchProfile();
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("token");
    navigate("/login");
  };

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
              <MessageSquareCode className="w-5 h-5 text-white" />
            </div>
            <span className="font-semibold text-lg">DataSpeakAI</span>
          </div>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1">
          {navigation.map((item) => (
            <NavLink
              key={item.name}
              to={item.href}
              end={item.href === "/dashboard"}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive
                    ? "bg-blue-50 text-blue-600"
                    : "text-gray-700 hover:bg-gray-50"
                }`
              }
            >
              <item.icon className="w-5 h-5" />
              {item.name}
            </NavLink>
          ))}
        </nav>

        <div className="p-4 border-t border-gray-200">
          <div className="bg-gradient-to-br from-blue-50 to-purple-50 rounded-lg p-4">
            <p className="text-sm font-medium mb-1">Upgrade to Pro</p>
            <p className="text-xs text-gray-600 mb-3">
              Unlock unlimited queries and advanced features
            </p>
            <Button size="sm" className="w-full">
              Upgrade Now
            </Button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Bar */}
        <header className="bg-white border-b border-gray-200 px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div>
                <h2 className="text-lg font-semibold">Welcome back!</h2>
                <p className="text-sm text-gray-600">
                  Manage your business data and AI insights
                </p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              {/* Organization Selector */}
              <Button variant="outline" className="gap-2 cursor-default hover:bg-transparent">
                <Building2 className="w-4 h-4" />
                <span className="text-sm">{organizationName}</span>
              </Button>

              <Button variant="ghost" size="icon" className="relative">
                <Bell className="w-5 h-5" />
                <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
              </Button>

              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" className="gap-2">
                    <Avatar className="w-8 h-8">
                      <AvatarImage src="" />
                      <AvatarFallback>JD</AvatarFallback>
                    </Avatar>
                    <span className="text-sm">{userName}</span>
                    <ChevronDown className="w-4 h-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  <DropdownMenuLabel>My Account</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={() => navigate("/dashboard/settings")} className="cursor-pointer">
                    Profile
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => navigate("/dashboard/settings")} className="cursor-pointer">
                    Billing
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => navigate("/dashboard/settings")} className="cursor-pointer">
                    Team
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={handleLogout} className="text-red-600 cursor-pointer">
                    Log out
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}