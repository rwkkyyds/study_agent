"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { auth, admin, UserResponse } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import AppShell from "@/components/app-shell";
import {
  Users,
  UserPlus,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Shield,
  ShieldCheck,
  User as UserIcon,
} from "lucide-react";

const roleLabel: Record<string, string> = {
  admin: "管理员",
  agent: "客服",
  customer: "用户",
};

const roleColor: Record<string, "default" | "secondary" | "success" | "warning" | "destructive"> = {
  admin: "destructive",
  agent: "warning",
  customer: "secondary",
};

export default function AdminUsersPage() {
  const router = useRouter();
  const [userList, setUserList] = useState<UserResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // 创建用户表单状态
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [newRole, setNewRole] = useState("agent");
  const [creating, setCreating] = useState(false);
  const [createMsg, setCreateMsg] = useState("");
  const [createErr, setCreateErr] = useState("");

  // 检查登录状态与角色
  useEffect(() => {
    if (!auth.isLoggedIn()) {
      router.push("/login");
      return;
    }
    auth.getMe().then((u) => {
      if (u.role !== "admin") {
        router.push("/chat");
      }
    }).catch(() => {});
  }, [router]);

  // 加载用户列表
  useEffect(() => {
    loadUsers();
  }, []);

  async function loadUsers() {
    setLoading(true);
    try {
      const list = await admin.listUsers();
      setUserList(list);
      setError("");
    } catch {
      setError("无法加载用户列表（需要管理员权限）");
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate() {
    if (!username.trim() || !password.trim()) {
      setCreateErr("用户名和密码不能为空");
      return;
    }
    if (password.length < 6) {
      setCreateErr("密码至少 6 位");
      return;
    }
    setCreating(true);
    setCreateErr("");
    setCreateMsg("");
    try {
      const user = await admin.createUser({
        username: username.trim(),
        password,
        role: newRole,
      });
      setCreateMsg(`创建成功：${user.username}（${roleLabel[user.role] ?? user.role}）`);
      setUsername("");
      setPassword("");
      await loadUsers();
    } catch (e) {
      setCreateErr(e instanceof Error ? e.message : "创建失败");
    } finally {
      setCreating(false);
    }
  }

  function formatDate(dateStr: string) {
    const d = new Date(dateStr);
    return d.toLocaleString("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  return (
    <AppShell>
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* 顶部标题栏 */}
        <div className="flex h-12 shrink-0 items-center justify-between border-b bg-card px-4">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-primary" />
            <h1 className="text-sm font-semibold">用户管理</h1>
          </div>
          <Badge variant="secondary" className="text-xs">
            共 {userList.length} 人
          </Badge>
        </div>

        <ScrollArea className="flex-1 p-4">
          <div className="mx-auto max-w-2xl space-y-4">
            {/* 创建用户表单 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <UserPlus className="h-4 w-4" />
                  创建账号
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="grid gap-3 sm:grid-cols-3">
                  <div className="space-y-1.5">
                    <label className="text-xs text-muted-foreground">用户名</label>
                    <Input
                      placeholder="用户名（至少 3 位）"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs text-muted-foreground">密码</label>
                    <Input
                      type="password"
                      placeholder="至少 6 位"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs text-muted-foreground">角色</label>
                    <select
                      value={newRole}
                      onChange={(e) => setNewRole(e.target.value)}
                      className="flex h-9 w-full items-center rounded-md border border-input bg-background px-3 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      <option value="agent">客服（agent）</option>
                      <option value="admin">管理员（admin）</option>
                      <option value="customer">用户（customer）</option>
                    </select>
                  </div>
                </div>

                {createMsg && (
                  <p className="flex items-center gap-1.5 text-xs text-emerald-600 dark:text-emerald-400">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    {createMsg}
                  </p>
                )}
                {createErr && (
                  <p className="flex items-center gap-1.5 text-xs text-destructive">
                    <AlertCircle className="h-3.5 w-3.5" />
                    {createErr}
                  </p>
                )}

                <Button
                  onClick={handleCreate}
                  disabled={creating || !username.trim() || !password.trim()}
                  className="gap-1.5"
                  size="sm"
                >
                  {creating ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <UserPlus className="h-3.5 w-3.5" />
                  )}
                  {creating ? "创建中…" : "创建账号"}
                </Button>
              </CardContent>
            </Card>

            {/* 用户列表 */}
            {loading ? (
              <div className="flex justify-center py-10">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : error && userList.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <AlertCircle className="mb-3 h-10 w-10 text-destructive" />
                <p className="text-sm text-muted-foreground">{error}</p>
              </div>
            ) : (
              <div className="space-y-2.5">
                {userList.map((user) => (
                  <Card key={user.id} className="transition-all hover:shadow-md">
                    <CardContent className="flex items-center gap-3 p-3.5">
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                        {user.role === "admin" ? (
                          <Shield className="h-4 w-4 text-primary" />
                        ) : (
                          <UserIcon className="h-4 w-4 text-primary" />
                        )}
                      </div>
                      <div className="min-w-0 flex-1 space-y-0.5">
                        <div className="flex items-center gap-2">
                          <span className="truncate text-sm font-medium">{user.username}</span>
                          <Badge variant={roleColor[user.role] ?? "secondary"} className="shrink-0 text-[10px]">
                            {roleLabel[user.role] ?? user.role}
                          </Badge>
                          {!user.is_active && (
                            <Badge variant="destructive" className="shrink-0 text-[10px]">
                              已禁用
                            </Badge>
                          )}
                        </div>
                        <p className="flex items-center gap-1 text-[10px] text-muted-foreground">
                          <Users className="h-3 w-3" />
                          ID #{user.id} · 创建于 {formatDate(user.created_at)}
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </ScrollArea>
      </div>
    </AppShell>
  );
}
