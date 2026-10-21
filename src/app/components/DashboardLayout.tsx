import { Outlet, NavLink, useNavigate } from "react-router";
import { useState, useEffect } from "react";
import { API_BASE_URL } from "../config/api";
import {
  LayoutDashboard,
  Database,
  Key,
  MessageSquare,
  FileText,
  Settings,
  Bell,
  ChevronDown,
  BookOpen,
  Lightbulb,
  Activity,
  Building2,
  MessageSquareCode,
  Sparkles,
  FileSpreadsheet,
  ShieldAlert,
} from "lucide-react";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "./ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "./ui/avatar";
import { formatRoleName } from "../utils/permissions";

const navigation = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "AI Assistant (Chat)", href: "/dashboard/chat", icon: MessageSquare },
  { name: "Databases", href: "/dashboard/databases", icon: Database },
  { name: "Knowledge Base", href: "/dashboard/knowledge-base", icon: BookOpen },
  { name: "DB AI Insights", href: "/dashboard/insights", icon: Sparkles },
  { name: "CSV / File Analytics", href: "/dashboard/csv-analytics", icon: FileSpreadsheet },
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
  const [userRole, setUserRole] = useState("Member");
  const [isPlatformAdmin, setIsPlatformAdmin] = useState(false);
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
        setUserRole(userData.role || "Member");
        setIsPlatformAdmin(Boolean(userData.is_platform_admin));

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

        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
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

          {/* Conditional Platform Admin Navigation */}
          {isPlatformAdmin && (
            <div className="pt-3 mt-3 border-t border-gray-200">
              <div className="px-3 mb-1 text-[10px] font-bold tracking-wider text-purple-700 uppercase">
                Platform Operations
              </div>
              <NavLink
                to="/admin"
                className={({ isActive }) =>
                  `flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors ${
                    isActive
                      ? "bg-purple-100/70 text-purple-800 font-semibold"
                      : "text-purple-700 hover:bg-purple-50"
                  }`
                }
              >
                <div className="flex items-center gap-3">
                  <ShieldAlert className="w-5 h-5 text-purple-600" />
                  <span>Platform Admin</span>
                </div>
                <Badge variant="secondary" className="bg-purple-100 text-purple-800 text-[10px] px-1.5 py-0 border-purple-200 font-semibold">
                  Root
                </Badge>
              </NavLink>
            </div>
          )}
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
              {/* Organization & Role Indicators */}
              <Button variant="outline" className="gap-2 cursor-default hover:bg-transparent">
                <Building2 className="w-4 h-4" />
                <span className="text-sm">{organizationName}</span>
              </Button>

              <Badge variant="outline" className="text-xs font-medium border-gray-300 text-gray-700 bg-gray-50/50">
                {formatRoleName(userRole)}
              </Badge>

              {isPlatformAdmin && (
                <Badge className="bg-purple-100 text-purple-800 hover:bg-purple-100 border border-purple-200 text-xs font-semibold gap-1">
                  <ShieldAlert className="w-3.5 h-3.5 text-purple-700" />
                  Platform Admin
                </Badge>
              )}

              <Button variant="ghost" size="icon" className="relative">
                <Bell className="w-5 h-5" />
                <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
              </Button>

              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" className="gap-2">
                    <Avatar className="w-8 h-8">
                      <AvatarImage src="" />
                      <AvatarFallback>{userName.charAt(0).toUpperCase()}</AvatarFallback>
                    </Avatar>
                    <span className="text-sm">{userName}</span>
                    <ChevronDown className="w-4 h-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  <DropdownMenuLabel className="flex flex-col gap-0.5">
                    <span>My Account</span>
                    <span className="text-xs font-normal text-gray-500">{userName}</span>
                  </DropdownMenuLabel>
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
                  {isPlatformAdmin && (
                    <>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem onClick={() => navigate("/admin")} className="cursor-pointer text-purple-700 font-semibold focus:text-purple-800 focus:bg-purple-50">
                        <ShieldAlert className="w-4 h-4 mr-2 text-purple-600" />
                        Platform Admin Control
                      </DropdownMenuItem>
                    </>
                  )}
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
