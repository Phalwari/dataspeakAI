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
  LogOut,
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
  const [userAvatar, setUserAvatar] = useState("");
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
        setUserAvatar(userData.avatar_url || "");
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

    window.addEventListener("profileUpdated", fetchProfile);
    return () => window.removeEventListener("profileUpdated", fetchProfile);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("token");
    navigate("/login");
  };

  return (
    <div className="flex h-screen bg-slate-50/50">
      {/* Sidebar */}
      <aside className="w-60 bg-white border-r border-slate-200/80 flex flex-col h-full shadow-xs shrink-0 select-none">
        {/* Sidebar Brand Header */}
        <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center shadow-xs shadow-blue-500/20 shrink-0">
              <MessageSquareCode className="w-3.5 h-3.5 text-white" />
            </div>
            <div className="min-w-0">
              <span className="font-bold text-[15px] tracking-tight text-slate-900 block leading-tight truncate">
                DataSpeak<span className="text-blue-600">AI</span>
              </span>
              <span className="text-[9.5px] font-semibold text-blue-600 tracking-wider uppercase block">
                Conversational BI
              </span>
            </div>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 px-2.5 py-2 space-y-0.5 overflow-y-auto custom-sidebar-scroll">
          {navigation.map((item) => (
            <NavLink
              key={item.name}
              to={item.href}
              end={item.href === "/dashboard"}
              className={({ isActive }) =>
                `group flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all duration-150 ${
                  isActive
                    ? "bg-blue-600 text-white shadow-xs shadow-blue-500/25 font-semibold"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-100/80"
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <item.icon
                    className={`w-4 h-4 shrink-0 transition-colors ${
                      isActive ? "text-white" : "text-slate-500 group-hover:text-slate-800"
                    }`}
                  />
                  <span className="truncate">{item.name}</span>
                </>
              )}
            </NavLink>
          ))}

          {/* Conditional Platform Admin Navigation */}
          {isPlatformAdmin && (
            <div className="pt-2 mt-2 border-t border-slate-200/80">
              <div className="px-2.5 mb-1 text-[9.5px] font-bold tracking-wider text-purple-700 uppercase">
                Platform Operations
              </div>
              <NavLink
                to="/admin"
                className={({ isActive }) =>
                  `group flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs transition-all duration-150 ${
                    isActive
                      ? "bg-purple-600 text-white font-semibold shadow-xs"
                      : "text-purple-700 hover:bg-purple-50"
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <div className="flex items-center gap-2.5">
                      <ShieldAlert
                        className={`w-4 h-4 shrink-0 transition-colors ${
                          isActive ? "text-white" : "text-purple-600"
                        }`}
                      />
                      <span>Platform Admin</span>
                    </div>
                    <Badge
                      variant="secondary"
                      className={`text-[9.5px] px-1.5 py-0 font-semibold ${
                        isActive
                          ? "bg-purple-700 text-white border-transparent"
                          : "bg-purple-100 text-purple-800 border-purple-200"
                      }`}
                    >
                      Root
                    </Badge>
                  </>
                )}
              </NavLink>
            </div>
          )}
        </nav>

        {/* Sidebar Footer — Compact User Profile */}
        <div className="p-2.5 border-t border-slate-100 bg-slate-50/50">
          <div className="flex items-center justify-between gap-2 p-1 rounded-lg hover:bg-slate-100/80 transition-colors">
            <div
              onClick={() => navigate("/dashboard/settings")}
              className="flex items-center gap-2 min-w-0 flex-1 cursor-pointer"
              title="Open Account Settings"
            >
              <Avatar className="w-7 h-7 shrink-0 ring-1 ring-slate-200">
                <AvatarImage src={userAvatar ? (userAvatar.startsWith("http") ? userAvatar : `${API_BASE_URL}${userAvatar}`) : ""} />
                <AvatarFallback className="text-[11px] font-semibold bg-blue-600 text-white">
                  {userName.charAt(0).toUpperCase()}
                </AvatarFallback>
              </Avatar>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-semibold text-slate-800 truncate leading-tight">{userName}</p>
                <p className="text-[10px] text-slate-400 truncate leading-tight mt-0.5">{organizationName}</p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={handleLogout}
              title="Sign Out"
              className="h-6 w-6 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-md shrink-0 p-1"
            >
              <LogOut className="w-3.5 h-3.5" />
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
                      <AvatarImage src={userAvatar ? (userAvatar.startsWith("http") ? userAvatar : `${API_BASE_URL}${userAvatar}`) : ""} />
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
