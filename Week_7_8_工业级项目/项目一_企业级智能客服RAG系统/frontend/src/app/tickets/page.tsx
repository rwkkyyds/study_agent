"use client";

import { KeyboardEvent, useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, auth, tickets, TicketResponse, UserResponse } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Avatar } from "@/components/ui/avatar";
import AppShell from "@/components/app-shell";
import {
  ArrowLeft,
  Ticket,
  MessageSquare,
  Loader2,
  AlertCircle,
  Clock,
  CheckCircle2,
  HelpCircle,
  Send,
  UserCheck,
  Lock,
  Search,
} from "lucide-react";

const statusLabel: Record<string, string> = {
  open: "待接入",
  assigned: "处理中",
  resolved: "已解决",
  closed: "已关闭",
};

const statusColor: Record<string, "default" | "secondary" | "success" | "warning" | "destructive"> = {
  open: "warning",
  assigned: "default",
  resolved: "success",
  closed: "secondary",
};

const priorityLabel: Record<string, string> = {
  low: "低",
  normal: "普通",
  medium: "中",
  high: "高",
  urgent: "紧急",
};

const senderLabel: Record<string, string> = {
  customer: "用户",
  agent: "客服",
  system: "系统",
};

const statusTabs = [
  { value: "all", label: "全部" },
  { value: "open", label: "待接入" },
  { value: "assigned", label: "处理中" },
  { value: "resolved", label: "已解决" },
  { value: "closed", label: "已关闭" },
] as const;

function getLastMessage(ticket: TicketResponse) {
  const messages = ticket.messages ?? [];
  if (messages.length === 0) return ticket.description;
  return messages[messages.length - 1].content;
}

export default function TicketsPage() {
  const router = useRouter();
  const [currentUser, setCurrentUser] = useState<UserResponse | null>(null);
  const [ticketList, setTicketList] = useState<TicketResponse[]>([]);
  const [selectedTicket, setSelectedTicket] = useState<TicketResponse | null>(null);
  const [replyText, setReplyText] = useState("");
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState("");
  const [activeStatus, setActiveStatus] = useState<(typeof statusTabs)[number]["value"]>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [liveNotice, setLiveNotice] = useState("");
  const selectedTicketId = selectedTicket?.id;

  const refreshTickets = useCallback(async () => {
    const list = await tickets.listTickets();
    setTicketList(list);
    return list;
  }, []);

  const upsertTicket = useCallback((updatedTicket: TicketResponse) => {
    setTicketList((prev) => {
      const exists = prev.some((ticket) => ticket.id === updatedTicket.id);
      if (!exists) return [updatedTicket, ...prev];
      return prev.map((ticket) => (ticket.id === updatedTicket.id ? updatedTicket : ticket));
    });
  }, []);

  useEffect(() => {
    let active = true;

    if (!auth.isLoggedIn()) {
      router.replace("/login");
      return;
    }

    async function loadInitialTickets() {
      try {
        const user = await auth.getMe();
        if (!active) return;

        if (user.role === "customer") {
          router.replace("/chat");
          return;
        }

        if (user.role !== "agent" && user.role !== "admin") {
          setError("当前账号无权访问客服工作台");
          setLoading(false);
          return;
        }

        setCurrentUser(user);
        const list = await tickets.listTickets();
        if (!active) return;
        setTicketList(list);
        setLoading(false);
      } catch (error) {
        if (!active) return;
        if (error instanceof ApiError && error.status === 401) {
          auth.logout();
          router.replace("/login");
          return;
        }
        if (error instanceof ApiError && error.status === 403) {
          router.replace("/chat");
          return;
        }
        setError("无法加载工单列表");
        setLoading(false);
      }
    }

    void loadInitialTickets();

    return () => {
      active = false;
    };
  }, [router]);

  async function loadTicketDetail(id: number) {
    try {
      const detail = await tickets.getTicket(id);
      setSelectedTicket(detail);
      upsertTicket(detail);
      setReplyText("");
    } catch {
      setError("无法加载工单详情");
    }
  }

  useEffect(() => {
    if (!currentUser) return;
    const controller = new AbortController();

    tickets
      .streamTicketListEvents(
        ({ type, ticket }) => {
          upsertTicket(ticket);
          setSelectedTicket((current) => (current?.id === ticket.id ? ticket : current));
          if (type === "ticket.created") {
            setLiveNotice(`收到新工单 #${ticket.id}`);
            void refreshTickets().catch(() => {
              setError("无法刷新最新工单列表");
            });
          }
        },
        controller.signal,
      )
      .catch((error) => {
        if (controller.signal.aborted) return;
        if (error instanceof ApiError && error.status === 401) {
          auth.logout();
          router.replace("/login");
          return;
        }
        setError("工单列表实时连接断开，请刷新页面重试");
      });

    return () => {
      controller.abort();
    };
  }, [currentUser, refreshTickets, router, upsertTicket]);

  useEffect(() => {
    if (!selectedTicketId) return;
    const controller = new AbortController();

    tickets
      .streamTicketEvents(
        selectedTicketId,
        ({ ticket }) => {
          setSelectedTicket((current) => (current?.id === ticket.id ? ticket : current));
          upsertTicket(ticket);
        },
        controller.signal,
      )
      .catch((error) => {
        if (controller.signal.aborted) return;
        if (error instanceof ApiError && error.status === 401) {
          auth.logout();
          router.replace("/login");
          return;
        }
        setError("工单实时连接断开，请刷新页面重试");
      });

    return () => {
      controller.abort();
    };
  }, [router, selectedTicketId, upsertTicket]);

  async function runTicketAction(action: () => Promise<TicketResponse>) {
    if (!selectedTicket) return;

    setActionLoading(true);
    try {
      const updated = await action();
      setSelectedTicket(updated);
      setReplyText("");
      await refreshTickets();
    } catch {
      setError("工单操作失败，请稍后重试");
    } finally {
      setActionLoading(false);
    }
  }

  async function handleReply() {
    if (!selectedTicket || !replyText.trim() || actionLoading) return;
    await runTicketAction(() => tickets.replyTicket(selectedTicket.id, replyText.trim()));
  }

  function handleReplyKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key !== "Enter" || event.shiftKey || event.nativeEvent.isComposing) return;
    event.preventDefault();
    void handleReply();
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

  const canHandle = currentUser?.role === "agent" || currentUser?.role === "admin";
  const pageTitle = "客服工作台";
  const statusCounts = statusTabs.reduce<Record<string, number>>((acc, tab) => {
    acc[tab.value] = tab.value === "all" ? ticketList.length : ticketList.filter((ticket) => ticket.status === tab.value).length;
    return acc;
  }, {});
  const normalizedSearch = searchQuery.trim().toLowerCase();
  const visibleTickets = ticketList.filter((ticket) => {
    if (activeStatus !== "all" && ticket.status !== activeStatus) return false;
    if (!normalizedSearch) return true;
    return [
      String(ticket.id),
      ticket.title,
      ticket.description,
      String(ticket.customer_id),
      String(ticket.agent_id ?? ""),
      getLastMessage(ticket),
    ].some((value) => value.toLowerCase().includes(normalizedSearch));
  });

  if (loading) {
    return (
      <AppShell>
        <div className="flex flex-1 items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      </AppShell>
    );
  }

  if (error) {
    return (
      <AppShell>
        <div className="flex flex-1 flex-col items-center justify-center gap-4">
          <AlertCircle className="h-8 w-8 text-destructive" />
          <p className="text-sm text-muted-foreground">{error}</p>
          <Button variant="outline" onClick={() => router.push("/chat")}>
            返回对话
          </Button>
        </div>
      </AppShell>
    );
  }

  if (selectedTicket) {
    const canReply = canHandle && selectedTicket.status !== "closed";
    const canClaim = canHandle && selectedTicket.status === "open";
    const canResolve = canHandle && selectedTicket.status === "assigned";
    const canClose = canHandle && selectedTicket.status === "resolved";

    return (
      <AppShell title={pageTitle}>
        <div className="flex flex-1 flex-col overflow-hidden">
          <div className="flex h-12 shrink-0 items-center gap-2 border-b bg-card px-3">
            <Button variant="ghost" size="icon" onClick={() => setSelectedTicket(null)}>
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <div className="flex min-w-0 items-center gap-2">
              <h1 className="truncate text-sm font-semibold">工单 #{selectedTicket.id}</h1>
              <Badge variant={statusColor[selectedTicket.status] ?? "secondary"} className="shrink-0 text-[10px]">
                {statusLabel[selectedTicket.status] ?? selectedTicket.status}
              </Badge>
            </div>
            {liveNotice && (
              <Button
                type="button"
                size="sm"
                variant="secondary"
                className="ml-auto h-8 text-xs"
                onClick={() => {
                  setSelectedTicket(null);
                  setLiveNotice("");
                }}
              >
                {liveNotice}
              </Button>
            )}
          </div>

          <ScrollArea className="flex-1 p-4">
            <div className="mx-auto max-w-2xl space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">{selectedTicket.title}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <p className="text-sm text-muted-foreground">{selectedTicket.description}</p>
                  <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Clock className="h-3.5 w-3.5" />
                      创建于 {formatDate(selectedTicket.created_at)}
                    </span>
                    <span className="flex items-center gap-1">
                      <HelpCircle className="h-3.5 w-3.5" />
                      优先级：{priorityLabel[selectedTicket.priority] ?? selectedTicket.priority}
                    </span>
                    {selectedTicket.agent_id && (
                      <span className="flex items-center gap-1">
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        客服 #{selectedTicket.agent_id}
                      </span>
                    )}
                  </div>

                  {canHandle && (
                    <div className="flex flex-wrap gap-2 pt-2">
                      {canClaim && (
                        <Button
                          size="sm"
                          disabled={actionLoading}
                          onClick={() => runTicketAction(() => tickets.claimTicket(selectedTicket.id))}
                          className="gap-1.5"
                        >
                          <UserCheck className="h-3.5 w-3.5" />
                          领取工单
                        </Button>
                      )}
                      {canResolve && (
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={actionLoading}
                          onClick={() => runTicketAction(() => tickets.resolveTicket(selectedTicket.id))}
                          className="gap-1.5"
                        >
                          <CheckCircle2 className="h-3.5 w-3.5" />
                          标记解决
                        </Button>
                      )}
                      {canClose && (
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={actionLoading}
                          onClick={() => runTicketAction(() => tickets.closeTicket(selectedTicket.id))}
                          className="gap-1.5"
                        >
                          <Lock className="h-3.5 w-3.5" />
                          关闭工单
                        </Button>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>

              <div className="space-y-3">
                <h2 className="flex items-center gap-2 text-sm font-semibold">
                  <MessageSquare className="h-4 w-4" />
                  对话记录
                </h2>

                {selectedTicket.messages && selectedTicket.messages.length > 0 ? (
                  selectedTicket.messages.map((msg) => (
                    <div key={msg.id} className="flex gap-3">
                      <Avatar
                        fallback={msg.sender_role === "customer" ? "U" : msg.sender_role === "system" ? "S" : "A"}
                        alt={senderLabel[msg.sender_role] ?? msg.sender_role}
                        className={msg.sender_role === "customer" ? "bg-primary" : "bg-muted"}
                      />
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-medium">
                            {senderLabel[msg.sender_role] ?? msg.sender_role}
                          </span>
                          <span className="text-[10px] text-muted-foreground">
                            {formatDate(msg.created_at)}
                          </span>
                        </div>
                        <p className="mt-1 text-sm leading-relaxed">{msg.content}</p>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-center text-sm text-muted-foreground">暂无对话记录</p>
                )}
              </div>

              {canReply && (
                <Card>
                  <CardContent className="space-y-3 p-4">
                    <Textarea
                      value={replyText}
                      onChange={(e) => setReplyText(e.target.value)}
                      onKeyDown={handleReplyKeyDown}
                      placeholder="输入回复，用户会在原聊天窗口看到..."
                      disabled={actionLoading}
                      className="min-h-24"
                    />
                    <div className="flex justify-end">
                      <Button
                        onClick={handleReply}
                        disabled={actionLoading || !replyText.trim()}
                        className="gap-1.5"
                      >
                        {actionLoading ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Send className="h-4 w-4" />
                        )}
                        发送回复
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          </ScrollArea>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell title={pageTitle}>
      <div className="flex flex-1 flex-col overflow-hidden">
        <div className="flex h-12 shrink-0 items-center justify-between border-b bg-card px-4">
          <div className="flex items-center gap-2">
            <Ticket className="h-5 w-5 text-primary" />
            <h1 className="text-sm font-semibold">{pageTitle}</h1>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="secondary" className="text-xs">
              共 {visibleTickets.length} / {ticketList.length} 条
            </Badge>
            {liveNotice && (
              <Button
                type="button"
                size="sm"
                variant="secondary"
                className="h-8 text-xs"
                onClick={() => setLiveNotice("")}
              >
                {liveNotice}
              </Button>
            )}
          </div>
        </div>

        <ScrollArea className="flex-1 p-4">
          <div className="mx-auto max-w-2xl space-y-3">
            <div className="space-y-3 rounded-lg border bg-card p-3">
              <div className="flex flex-wrap gap-2">
                {statusTabs.map((tab) => (
                  <Button
                    key={tab.value}
                    type="button"
                    size="sm"
                    variant={activeStatus === tab.value ? "secondary" : "ghost"}
                    onClick={() => setActiveStatus(tab.value)}
                    className="h-8 gap-1.5 text-xs"
                  >
                    {tab.label}
                    <Badge variant="outline" className="h-4 px-1.5 text-[10px]">
                      {statusCounts[tab.value] ?? 0}
                    </Badge>
                  </Button>
                ))}
              </div>
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder={canHandle ? "搜索工单号、用户 ID、问题或最后消息..." : "搜索我的工单..."}
                  className="pl-9"
                />
              </div>
            </div>

            {ticketList.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <Ticket className="mb-3 h-12 w-12 text-muted-foreground/40" />
                <p className="text-sm text-muted-foreground">暂无工单</p>
                <p className="mt-1 text-xs text-muted-foreground/60">
                  {canHandle ? "待接入和已领取的工单会显示在这里" : "在对话中转人工后会显示在这里"}
                </p>
              </div>
            ) : visibleTickets.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <Search className="mb-3 h-12 w-12 text-muted-foreground/40" />
                <p className="text-sm text-muted-foreground">没有匹配的工单</p>
                <p className="mt-1 text-xs text-muted-foreground/60">调整状态筛选或搜索关键词后再试</p>
              </div>
            ) : (
              visibleTickets.map((t) => (
                <Card
                  key={t.id}
                  className="cursor-pointer transition-all hover:shadow-md active:scale-[0.99]"
                  onClick={() => loadTicketDetail(t.id)}
                >
                  <CardContent className="flex items-center gap-4 p-4">
                    <div className="flex-1 space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium">{t.title}</span>
                        <Badge variant={statusColor[t.status] ?? "secondary"} className="text-[10px]">
                          {statusLabel[t.status] ?? t.status}
                        </Badge>
                      </div>
                      <p className="line-clamp-1 text-xs text-muted-foreground">{t.description}</p>
                      <p className="line-clamp-1 text-xs text-foreground/70">
                        最后消息：{getLastMessage(t)}
                      </p>
                      <div className="flex gap-3 text-[10px] text-muted-foreground">
                        <span>{formatDate(t.created_at)}</span>
                        <span>{priorityLabel[t.priority] ?? t.priority}</span>
                        {t.agent_id && <span>客服 #{t.agent_id}</span>}
                      </div>
                    </div>
                    <MessageSquare className="h-4 w-4 shrink-0 text-muted-foreground/40" />
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        </ScrollArea>
      </div>
    </AppShell>
  );
}
