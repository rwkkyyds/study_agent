"use client";

import { useRouter, usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { auth } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { useTheme } from "@/components/theme-provider";
import {
  ArrowLeft,
  Bot,
  MessageCircle,
  Ticket,
  LogOut,
  Sun,
  Moon,
  User,
  BookOpen,
  Users,
} from "lucide-react";

interface AppShellProps {
  children: React.ReactNode;
  /** 可选：当前页面的标题，默认自动从路径识别 */
  title?: string;
  /** 可选：是否显示返回按钮（默认 true） */
  showBack?: boolean;
  /** 可选：返回按钮点击行为（默认 router.back()） */
  onBack?: () => void;
  /** 额外右侧操作区 */
  extra?: React.ReactNode;
}

const pageTitles: Record<string, string> = {
  "/chat": "智能客服",
  "/tickets": "客服工作台",
  "/documents": "知识库",
  "/admin/users": "用户管理",
};

export default function AppShell({
  children,
  title,
  showBack = true,
  onBack,
  extra,
}: AppShellProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { theme, toggleTheme } = useTheme();
  const [userName, setUserName] = useState("");
  const [userRole, setUserRole] = useState("");

  // 检查登录态
  useEffect(() => {
    if (!auth.isLoggedIn()) {
      router.push("/login");
      return;
    }
    auth.getMe().then((u) => {
      setUserName(u.username);
      setUserRole(u.role);
    }).catch(() => {});
  }, [router]);

  const pageTitle =
    title ??
    (pathname === "/tickets" && (userRole === "agent" || userRole === "admin")
      ? "客服工作台"
      : pageTitles[pathname]) ??
    pathname.replace("/", "");

  function handleLogout() {
    auth.logout();
    router.push("/login");
  }

  function handleBack() {
    if (onBack) {
      onBack();
    } else {
      router.back();
    }
  }

  const isStaff = userRole === "agent" || userRole === "admin";
  const canAccessKnowledge = isStaff;

  return (
    <div className="flex h-screen flex-col bg-background">
      {/* ====== 全局导航栏（始终可见） ====== */}
      <header className="flex h-14 shrink-0 items-center justify-between border-b bg-card px-3 shadow-sm">
        {/* 左侧：Logo + 页面标题 */}
        <div className="flex items-center gap-2 min-w-0">
          {/* 品牌 Logo */}
          <div
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary cursor-pointer"
            onClick={() => router.push(userRole === "agent" || userRole === "admin" ? "/tickets" : "/chat")}
            title="回到主页"
          >
            <Bot className="h-4 w-4 text-primary-foreground" />
          </div>

          {/* 分隔 */}
          <span className="hidden h-5 w-px bg-border sm:block" />

          {/* 导航链接 */}
          {showBack && pathname !== "/chat" && (
            <Button
              variant="ghost"
              size="icon"
              onClick={handleBack}
              title="返回"
              className="hidden h-8 w-8 sm:inline-flex"
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
          )}

          <span className="hidden max-w-[160px] truncate text-sm font-medium text-foreground lg:block">
            {pageTitle}
          </span>

          <nav className="hidden items-center gap-1 sm:flex">
            {userRole === "customer" && (
              <Button
                variant={pathname === "/chat" ? "secondary" : "ghost"}
                size="sm"
                onClick={() => router.push("/chat")}
                className="gap-1.5 text-xs"
              >
                <MessageCircle className="h-3.5 w-3.5" />
                对话
              </Button>
            )}
            {isStaff && (
              <Button
                variant={pathname === "/tickets" ? "secondary" : "ghost"}
                size="sm"
                onClick={() => router.push("/tickets")}
                className="gap-1.5 text-xs"
              >
                <Ticket className="h-3.5 w-3.5" />
                客服工作台
              </Button>
            )}
            {canAccessKnowledge && (
              <Button
                variant={pathname === "/documents" ? "secondary" : "ghost"}
                size="sm"
                onClick={() => router.push("/documents")}
                className="gap-1.5 text-xs"
              >
                <BookOpen className="h-3.5 w-3.5" />
                知识库
              </Button>
            )}
            {userRole === "admin" && (
              <Button
                variant={pathname === "/admin/users" ? "secondary" : "ghost"}
                size="sm"
                onClick={() => router.push("/admin/users")}
                className="gap-1.5 text-xs"
              >
                <Users className="h-3.5 w-3.5" />
                用户管理
              </Button>
            )}
          </nav>
        </div>

        {/* 右侧：用户信息 + 主题切换 + 退出 */}
        <div className="flex items-center gap-1">
          {extra}

          {/* 主题切换按钮 */}
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            title={theme === "dark" ? "切换亮色模式" : "切换暗色模式"}
            className="text-muted-foreground hover:text-foreground"
          >
            {theme === "dark" ? (
              <Sun className="h-4 w-4" />
            ) : (
              <Moon className="h-4 w-4" />
            )}
          </Button>

          {/* 用户名 */}
          {userName && (
            <span className="hidden items-center gap-1 text-xs text-muted-foreground md:flex">
              <User className="h-3.5 w-3.5" />
              {userName}
            </span>
          )}

          {/* 退出登录 */}
          <Button
            variant="ghost"
            size="sm"
            onClick={handleLogout}
            className="gap-1.5 text-xs text-muted-foreground hover:text-destructive"
            title="退出登录"
          >
            <LogOut className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">退出</span>
          </Button>
        </div>
      </header>

      {/* ====== 页面内容 ====== */}
      {children}
    </div>
  );
}
