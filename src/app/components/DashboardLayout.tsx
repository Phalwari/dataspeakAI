import { Outlet, NavLink, useNavigate, useLocation } from "react-router";
import { useState, useEffect, useRef } from "react";
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
  ChevronLeft,
  ChevronRight,
  BookOpen,
  Lightbulb,
  Activity,
  Building2,
  MessageSquareCode,
  Sparkles,
  FileSpreadsheet,
  BarChart3,
  LogOut,
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

interface NavItem {
  name: string;
  href: string;
  icon: any;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

const navigationGroups: NavSection[] = [
  {
    title: "OVERVIEW",
    items: [
      { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
      { name: "AI Assistant (Chat)", href: "/dashboard/chat", icon: MessageSquare },
    ],
  },
  {
    title: "DATA & ANALYTICS",
    items: [
      { name: "Databases", href: "/dashboard/databases", icon: Database },
      { name: "Knowledge Base", href: "/dashboard/knowledge-base", icon: BookOpen },
      { name: "Analytics & Visualization", href: "/dashboard/analytics", icon: BarChart3 },
      { name: "DB AI Insights", href: "/dashboard/insights", icon: Sparkles },
      { name: "CSV / File Analytics", href: "/dashboard/csv-analytics", icon: FileSpreadsheet },
      { name: "AI Insights", href: "/dashboard/ai-insights", icon: Lightbulb },
    ],
  },
  {
    title: "AGENTS & KEYS",
    items: [
      { name: "Chatbot Widget", href: "/dashboard/chatbot", icon: MessageSquareCode },
      { name: "API Keys", href: "/dashboard/api-keys", icon: Key },
    ],
  },
  {
    title: "SYSTEM",
    items: [
      { name: "Usage", href: "/dashboard/usage", icon: Activity },
      { name: "Logs", href: "/dashboard/logs", icon: FileText },
      { name: "Settings", href: "/dashboard/settings", icon: Settings },
    ],
  },
];

export function DashboardLayout() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  // Chat page manages its own scrolling, so <main> must not scroll or pad on this route.
  // (exact match so /dashboard/chatbot is NOT treated as the chat route)
  const isChatRoute = pathname.replace(/\/$/, "") === "/dashboard/chat";

  const [userName, setUserName] = useState("Loading...");
  const [organizationName, setOrganizationName] = useState("Loading...");
  const [isCollapsed, setIsCollapsed] = useState(() => {
    try {
      // Small screens always start with the compact icon-only sidebar
      if (window.innerWidth < 768) return true;
      return localStorage.getItem("dataspeak_sidebar_collapsed") === "true";
    } catch {
      return false;
    }
  });

  const toggleSidebar = () => {
    setIsCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem("dataspeak_sidebar_collapsed", String(next));
      } catch { }
      return next;
    });
  };

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

  const [thumbTop, setThumbTop] = useState(0);
  const [canScroll, setCanScroll] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const navRef = useRef<HTMLElement | null>(null);
  const trackRef = useRef<HTMLDivElement | null>(null);
  const dragStartY = useRef(0);
  const dragStartScrollTop = useRef(0);

  const THUMB_HEIGHT = 56; // Slightly taller compact pill (increased from 36px)

  const updateScrollState = () => {
    const nav = navRef.current;
    const track = trackRef.current;
    if (!nav) return;
    const scrollRange = nav.scrollHeight - nav.clientHeight;
    const isScrollable = scrollRange > 2;
    setCanScroll(isScrollable);
    if (!isScrollable) {
      setThumbTop(0);
      return;
    }
    const trackHeight = track?.clientHeight || nav.clientHeight;
    const maxTravel = Math.max(0, trackHeight - THUMB_HEIGHT);
    const progress = Math.min(1, Math.max(0, nav.scrollTop / scrollRange));
    setThumbTop(progress * maxTravel);
  };

  const handleNavScroll = () => {
    if (isDragging) return;
    updateScrollState();
  };

  const handleThumbMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
    dragStartY.current = e.clientY;
    dragStartScrollTop.current = navRef.current ? navRef.current.scrollTop : 0;
  };

  const handleTrackClick = (e: React.MouseEvent) => {
    const track = trackRef.current;
    const nav = navRef.current;
    if (!track || !nav) return;
    const rect = track.getBoundingClientRect();
    const clickY = e.clientY - rect.top;
    const trackHeight = rect.height;
    const maxTravel = Math.max(1, trackHeight - THUMB_HEIGHT);
    const targetProgress = Math.min(1, Math.max(0, (clickY - THUMB_HEIGHT / 2) / maxTravel));
    nav.scrollTop = targetProgress * (nav.scrollHeight - nav.clientHeight);
  };

  useEffect(() => {
    updateScrollState();
    const nav = navRef.current;
    if (!nav) return;

    const resizeObserver = new ResizeObserver(() => {
      updateScrollState();
    });
    resizeObserver.observe(nav);

    window.addEventListener("resize", updateScrollState);
    return () => {
      resizeObserver.disconnect();
      window.removeEventListener("resize", updateScrollState);
    };
  }, [isCollapsed]);

  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      const nav = navRef.current;
      const track = trackRef.current;
      if (!nav || !track) return;
      const trackHeight = track.clientHeight;
      const maxTravel = Math.max(1, trackHeight - THUMB_HEIGHT);
      const scrollRange = nav.scrollHeight - nav.clientHeight;
      const deltaY = e.clientY - dragStartY.current;
      nav.scrollTop = dragStartScrollTop.current + (deltaY / maxTravel) * scrollRange;
      const progress = Math.min(1, Math.max(0, nav.scrollTop / scrollRange));
      setThumbTop(progress * maxTravel);
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDragging]);

  const handleLogout = () => {
    localStorage.removeItem("token");
    navigate("/login");
  };

  return (
    <div className="flex h-screen bg-slate-50/60 font-sans">
      {/* Sidebar with dynamic collapse and boundary light-up toggle button */}
      <aside
        className={`relative bg-white border-r border-slate-200/80 flex flex-col transition-all duration-300 ease-in-out shrink-0 select-none z-20 ${isCollapsed ? "w-20" : "w-64"
          }`}
      >
        {/* Circular Collapse Toggle Button on Border line matching Pic 2 */}
        <div className="absolute top-1/2 -translate-y-1/2 right-0 translate-x-1/2 z-30 group">
          <button
            type="button"
            onClick={toggleSidebar}
            aria-label={isCollapsed ? "Expand menu" : "Collapse menu"}
            className="w-8 h-8 rounded-full bg-white border border-slate-200 shadow-[0_1px_3px_rgba(0,0,0,0.06)] hover:border-blue-500 hover:shadow-[0_2px_8px_rgba(59,130,246,0.18)] flex items-center justify-center transition-all duration-150 cursor-pointer outline-none"
          >
            {isCollapsed ? (
              <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-blue-500 transition-colors stroke-[2]" />
            ) : (
              <ChevronLeft className="w-4 h-4 text-slate-400 group-hover:text-blue-500 transition-colors stroke-[2]" />
            )}
          </button>

          {/* Custom Dark Tooltip matching Pic 2 */}
          <div className="absolute top-full mt-2 left-1/2 -translate-x-1/2 px-2.5 py-1 bg-slate-900 text-white text-[11px] font-medium rounded-md shadow-lg whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity duration-150 pointer-events-none z-50">
            <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-2 h-2 bg-slate-900 rotate-45" />
            <span className="relative z-10">{isCollapsed ? "Expand menu" : "Collapse menu"}</span>
          </div>
        </div>

        {/* Sidebar Header / Brand Logo */}
        <div className={`p-5 border-b border-slate-100 flex items-center ${isCollapsed ? "justify-center px-2" : "gap-3"}`}>
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center shadow-sm shadow-blue-500/20 shrink-0">
            <MessageSquareCode className="w-5 h-5 text-white" />
          </div>
          {!isCollapsed && (
            <div className="flex flex-col overflow-hidden">
              <span className="font-bold text-lg text-slate-900 tracking-tight leading-none">
                DataSpeak<span className="text-blue-600">AI</span>
              </span>
              <span className="text-[10px] text-slate-400 font-medium tracking-wide mt-1">Enterprise Platform</span>
            </div>
          )}
        </div>

        {/* Navigation Sections with custom slim scrollbar matching Pic 3 (No arrows, 36px height, lights up blue on pointer hover) */}
        <div className="relative flex-1 min-h-0 flex flex-col">
          <nav
            ref={navRef}
            onScroll={handleNavScroll}
            className="flex-1 px-3 py-4 space-y-4 overflow-y-auto overflow-x-hidden no-scrollbar"
          >
            {navigationGroups.map((group, gIdx) => (
              <div key={gIdx} className="space-y-1">
                {/* Category Title */}
                {!isCollapsed ? (
                  <div className="text-[10.5px] font-bold text-slate-400 tracking-wider uppercase px-3 pt-2 pb-1">
                    {group.title}
                  </div>
                ) : (
                  gIdx > 0 && <div className="border-t border-slate-100 my-2 mx-1" />
                )}

                {/* Items in Category */}
                {group.items.map((item) => (
                  <NavLink
                    key={item.name}
                    to={item.href}
                    end={item.href === "/dashboard"}
                    title={isCollapsed ? item.name : undefined}
                    className={({ isActive }) =>
                      `group flex items-center rounded-xl text-sm font-medium transition-all duration-150 ${isCollapsed
                        ? "justify-center h-10 w-10 mx-auto"
                        : "gap-3 px-3 py-2.5 w-full"
                      } ${isActive
                        ? "bg-blue-600 text-white shadow-sm shadow-blue-500/25"
                        : "text-slate-600 hover:text-slate-900 hover:bg-slate-100/80"
                      }`
                    }
                  >
                    {({ isActive }) => (
                      <>
                        <item.icon
                          className={`w-5 h-5 shrink-0 transition-colors ${isActive
                              ? "text-white"
                              : "text-slate-500 group-hover:text-slate-800"
                            }`}
                        />
                        {!isCollapsed && <span className="truncate">{item.name}</span>}
                      </>
                    )}
                  </NavLink>
                ))}
              </div>
            ))}
          </nav>

          {/* Custom Compact Scrollbar Thumb matching Pic 3 (Strictly 36px height, NO arrow buttons, lights up blue on pointer hover) */}
          {canScroll && !isCollapsed && (
            <div
              ref={trackRef}
              onClick={handleTrackClick}
              className="absolute right-0.5 top-2 bottom-2 w-2 z-10 select-none flex justify-end"
            >
              <div
                onMouseDown={handleThumbMouseDown}
                style={{
                  transform: `translateY(${thumbTop}px)`,
                  height: `${THUMB_HEIGHT}px`,
                }}
                className={`w-1 rounded-full cursor-pointer transition-all duration-150 mr-0.5 ${isDragging
                    ? "bg-slate-600 w-1.5 shadow-sm"
                    : "bg-slate-300 hover:bg-slate-600 hover:w-1.5"
                  }`}
                title="Scroll"
              />
            </div>
          )}
        </div>

        {/* Bottom Profile Footer (Matching Reference Image) */}
        <div className="p-3 border-t border-slate-100 mt-auto bg-slate-50/40">
          <div className={`flex items-center ${isCollapsed ? "justify-center" : "justify-between"} p-1.5 rounded-xl transition-colors`}>
            <div className="flex items-center gap-2.5 overflow-hidden">
              <div className="w-8 h-8 rounded-full bg-blue-600 text-white font-semibold flex items-center justify-center text-xs shrink-0 shadow-sm">
                {userName ? userName.charAt(0).toUpperCase() : "A"}
              </div>
              {!isCollapsed && (
                <div className="flex flex-col overflow-hidden text-left">
                  <span className="text-xs font-semibold text-slate-800 truncate leading-tight">
                    {userName}
                  </span>
                  <span className="text-[10px] text-slate-400 truncate leading-tight mt-0.5">
                    Administrator
                  </span>
                </div>
              )}
            </div>
            {!isCollapsed && (
              <button
                type="button"
                onClick={handleLogout}
                title="Log out"
                className="text-slate-400 hover:text-rose-600 transition-colors p-1.5 rounded-lg hover:bg-slate-100 shrink-0"
              >
                <LogOut className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 min-w-0 flex flex-col overflow-hidden">
        {/* Top Bar Header */}
        <header className="bg-white border-b border-slate-200/80 px-3 sm:px-6 py-3 sm:py-4 shrink-0 shadow-[0_1px_2px_rgba(0,0,0,0.03)]">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-4 min-w-0">
              <div className="min-w-0">
                <h2 className="text-base sm:text-lg font-bold text-slate-900 tracking-tight truncate">Welcome back!</h2>
                <p className="hidden sm:block text-xs text-slate-500 mt-0.5 truncate">
                  Manage your business data and AI insights
                </p>
              </div>
            </div>

            <div className="flex items-center gap-1.5 sm:gap-3 shrink-0">
              {/* Organization Selector */}
              <Button variant="outline" className="gap-2 cursor-default hover:bg-transparent h-9 text-xs font-medium border-slate-200 px-2.5 sm:px-3">
                <Building2 className="w-3.5 h-3.5 text-slate-500" />
                <span className="hidden md:inline text-slate-700">{organizationName}</span>
              </Button>

              <Button variant="ghost" size="icon" className="relative h-9 w-9 text-slate-600 hover:text-slate-900">
                <Bell className="w-4 h-4" />
                <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-rose-500 rounded-full" />
              </Button>

              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" className="gap-2 h-9 pl-1 pr-2 hover:bg-slate-100/80">
                    <Avatar className="w-7 h-7">
                      <AvatarImage src="" />
                      <AvatarFallback className="text-xs font-semibold bg-slate-100 text-slate-700">JD</AvatarFallback>
                    </Avatar>
                    <span className="hidden sm:inline text-xs font-medium text-slate-700 max-w-[140px] truncate">{userName}</span>
                    <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56 text-xs">
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

        {/* Page Content: chat route gets a fixed-height, non-scrolling, padding-free container
            (ChatPage scrolls its own list and messages); every other page behaves as before. */}
        <main
          className={`flex-1 min-h-0 bg-slate-50/50 ${isChatRoute ? "overflow-hidden p-0" : "overflow-auto p-3 sm:p-6"
            }`}
        >
          <Outlet />
        </main>
      </div>
    </div>
  );
}