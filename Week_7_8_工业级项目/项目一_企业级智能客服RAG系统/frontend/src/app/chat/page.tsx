"use client";

import { useCallback, useEffect, useRef, useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  ApiError,
  auth,
  chat,
  ChatResponse,
  health,
  tickets,
  TicketMessage,
  TicketResponse,
  UserResponse,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import AppShell from "@/components/app-shell";
import {
  Send,
  Ticket,
  FileText,
  Loader2,
  AlertCircle,
  Headphones,
} from "lucide-react";

interface Message {
  role: "user" | "assistant";
  content: string;
  localId?: string;
  intent?: string;
  model?: string | null;
  sources?: ChatResponse["sources"];
  ticket_id?: number | null;
  ticketMessageId?: number;
}

const AVAILABLE_MODELS = [
  { value: "qwen-plus", label: "通义千问 Plus（推荐）" },
  { value: "qwen-max", label: "通义千问 Max（最强）" },
  { value: "qwen-turbo", label: "通义千问 Turbo（最快）" },
  { value: "qwen-coder-plus", label: "通义千问 Coder Plus" },
  { value: "qwen-coder-turbo", label: "通义千问 Coder Turbo" },
] as const;

const DEFAULT_MESSAGES: Message[] = [
  {
    role: "assistant",
    content: "您好！我是智能客服助手，可以为您查询订单信息、回答知识库问题。请问有什么可以帮助您的？",
  },
];

function messagesKey(userId: number) {
  return "chat_messages_" + userId;
}

function activeTicketKey(userId: number) {
  return "chat_active_ticket_" + userId;
}

function ticketStatusKey(userId: number) {
  return "chat_active_ticket_status_" + userId;
}

function ticketMessageToChatMessage(message: TicketMessage): Message {
  return {
    role: message.sender_role === "customer" ? "user" : "assistant",
    content: message.content,
    ticketMessageId: message.id,
  };
}

const intentLabel: Record<string, string> = {
  knowledge: "知识问答",
  order: "订单查询",
  ticket: "工单处理",
  greeting: "问候",
  human: "转人工",
};

const intentColor: Record<string, "default" | "secondary" | "success" | "warning"> = {
  knowledge: "default",
  order: "secondary",
  ticket: "warning",
  greeting: "secondary",
  human: "success",
};

const ticketStatusLabel: Record<string, string> = {
  open: "等待客服接入",
  assigned: "人工客服处理中",
  resolved: "已解决",
  closed: "已关闭",
};

function getSourceTitle(source: ChatResponse["sources"][number]) {
  const title = source.metadata?.title;
  const sourceName = source.metadata?.source;

  if (typeof title === "string" && title.trim()) return title.trim();
  if (typeof sourceName === "string" && sourceName.trim()) return sourceName.trim();
  return source.id;
}

function getSourceSnippet(source: ChatResponse["sources"][number]) {
  if (typeof source.content !== "string") return "";
  return source.content.trim();
}

function MarkdownMessage({ content }: { content: string }) {
  if (!content.trim()) return null;

  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      skipHtml
      components={{
        p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
        strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
        h1: ({ children }) => <h1 className="mb-2 text-base font-semibold">{children}</h1>,
        h2: ({ children }) => <h2 className="mb-2 text-sm font-semibold">{children}</h2>,
        h3: ({ children }) => <h3 className="mb-2 text-sm font-semibold">{children}</h3>,
        ul: ({ children }) => <ul className="mb-2 list-disc space-y-1 pl-5 last:mb-0">{children}</ul>,
        ol: ({ children }) => <ol className="mb-2 list-decimal space-y-1 pl-5 last:mb-0">{children}</ol>,
        li: ({ children }) => <li className="pl-1">{children}</li>,
        blockquote: ({ children }) => (
          <blockquote className="mb-2 border-l-2 border-border pl-3 text-muted-foreground last:mb-0">
            {children}
          </blockquote>
        ),
        a: ({ children, href }) => (
          <a
            href={href}
            target="_blank"
            rel="noreferrer"
            className="font-medium text-primary underline underline-offset-2"
          >
            {children}
          </a>
        ),
        pre: ({ children }) => (
          <pre className="mb-2 max-w-full overflow-x-auto rounded-lg bg-background/80 p-3 text-xs leading-relaxed text-foreground last:mb-0">
            {children}
          </pre>
        ),
        code: ({ children, className }) => {
          const isBlock = Boolean(className);
          return (
            <code
              className={
                isBlock
                  ? "block whitespace-pre font-mono"
                  : "rounded bg-background/70 px-1 py-0.5 font-mono text-[0.85em]"
              }
            >
              {children}
            </code>
          );
        },
        table: ({ children }) => (
          <div className="mb-2 max-w-full overflow-x-auto last:mb-0">
            <table className="w-full border-collapse text-xs">{children}</table>
          </div>
        ),
        th: ({ children }) => (
          <th className="border border-border bg-background/70 px-2 py-1 text-left font-semibold">
            {children}
          </th>
        ),
        td: ({ children }) => <td className="border border-border px-2 py-1">{children}</td>,
      }}
    >
      {content}
    </ReactMarkdown>
  );
}

export default function ChatPage() {
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>(DEFAULT_MESSAGES);
  const [currentUser, setCurrentUser] = useState<UserResponse | null>(null);
  const [chatStorageReady, setChatStorageReady] = useState(false);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedModel, setSelectedModel] = useState("qwen-plus");
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);
  const [activeTicketId, setActiveTicketId] = useState<number | null>(null);
  const [activeTicketStatus, setActiveTicketStatus] = useState<string | null>(null);
  const [showNewMessages, setShowNewMessages] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const shouldStickToBottomRef = useRef(true);

  const mergeTicketMessages = useCallback((ticket: TicketResponse) => {
    setActiveTicketStatus(ticket.status);
    setMessages((prev) => {
      const next = [...prev];
      const sortedMessages = [...(ticket.messages ?? [])].sort(
        (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
      );

      for (const ticketMessage of sortedMessages) {
        const mapped = ticketMessageToChatMessage(ticketMessage);
        const alreadyExists = next.some((item) => item.ticketMessageId === ticketMessage.id);
        if (alreadyExists) continue;

        const optimisticIndex = next.findIndex(
          (item) => item.role === mapped.role && item.content === mapped.content && !item.ticketMessageId,
        );

        if (optimisticIndex >= 0) {
          next[optimisticIndex] = mapped;
        } else {
          next.push(mapped);
        }
      }

      return next;
    });

    if (ticket.status === "resolved" || ticket.status === "closed") {
      setActiveTicketId(null);
    }
  }, []);

  const loadActiveTicket = useCallback(
    async (ticketId: number) => {
      try {
        const ticket = await tickets.getTicket(ticketId);
        mergeTicketMessages(ticket);
      } catch (error) {
        if (error instanceof ApiError && [403, 404].includes(error.status)) {
          setActiveTicketId(null);
          setActiveTicketStatus(null);
        }
      }
    },
    [mergeTicketMessages],
  );

  useEffect(() => {
    let active = true;

    health
      .checkHealth()
      .then(() => {
        if (active) setBackendOnline(true);
      })
      .catch(() => {
        if (active) setBackendOnline(false);
      });

    auth
      .getMe()
      .then((user) => {
        if (!active) return;

        if (user.role !== "customer") {
          router.replace("/tickets");
          return;
        }

        setCurrentUser(user);
        let restoredMessages: Message[] | null = null;
        let restoredTicketId: number | null = null;
        let restoredTicketStatus: string | null = null;

        try {
          const savedMessages = localStorage.getItem(messagesKey(user.id));
          if (savedMessages) {
            const parsed = JSON.parse(savedMessages);
            if (Array.isArray(parsed) && parsed.length > 0) {
              restoredMessages = parsed;
            }
          }

          const savedTicketId = localStorage.getItem(activeTicketKey(user.id));
          if (savedTicketId) {
            const parsedTicketId = Number(savedTicketId);
            if (Number.isFinite(parsedTicketId)) {
              restoredTicketId = parsedTicketId;
            }
          }

          restoredTicketStatus = localStorage.getItem(ticketStatusKey(user.id));
        } catch {
          // 忽略本地缓存解析错误，使用默认欢迎消息。
        }

        window.setTimeout(() => {
          if (!active) return;
          if (restoredMessages) setMessages(restoredMessages);
          if (restoredTicketId) {
            setActiveTicketId(restoredTicketId);
            setActiveTicketStatus(restoredTicketStatus || "open");
            void loadActiveTicket(restoredTicketId);
          }
          setChatStorageReady(true);
        }, 0);
      })
      .catch((error) => {
        if (error instanceof ApiError && error.status === 401) {
          auth.logout();
        }
        router.replace("/login");
      });

    return () => {
      active = false;
    };
  }, [loadActiveTicket, router]);

  const scrollToBottom = useCallback(() => {
    window.requestAnimationFrame(() => {
      if (!scrollRef.current) return;
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
      shouldStickToBottomRef.current = true;
      setShowNewMessages(false);
    });
  }, []);

  const handleScroll = useCallback(() => {
    const element = scrollRef.current;
    if (!element) return;
    const distanceToBottom = element.scrollHeight - element.scrollTop - element.clientHeight;
    const nearBottom = distanceToBottom < 96;
    shouldStickToBottomRef.current = nearBottom;
    if (nearBottom) {
      setShowNewMessages(false);
    }
  }, []);

  useEffect(() => {
    if (shouldStickToBottomRef.current) {
      scrollToBottom();
    } else {
      setShowNewMessages(true);
    }
  }, [messages, scrollToBottom]);

  useEffect(() => {
    if (!chatStorageReady || !currentUser) return;
    localStorage.setItem(messagesKey(currentUser.id), JSON.stringify(messages));
  }, [chatStorageReady, currentUser, messages]);

  useEffect(() => {
    if (!chatStorageReady || !currentUser) return;

    if (activeTicketId) {
      localStorage.setItem(activeTicketKey(currentUser.id), String(activeTicketId));
      if (activeTicketStatus) {
        localStorage.setItem(ticketStatusKey(currentUser.id), activeTicketStatus);
      }
    } else {
      localStorage.removeItem(activeTicketKey(currentUser.id));
      localStorage.removeItem(ticketStatusKey(currentUser.id));
    }
  }, [activeTicketId, activeTicketStatus, chatStorageReady, currentUser]);

  useEffect(() => {
    if (!activeTicketId) return;
    const controller = new AbortController();

    tickets
      .streamTicketEvents(
        activeTicketId,
        ({ ticket }) => {
          setBackendOnline(true);
          mergeTicketMessages(ticket);
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
        setBackendOnline(false);
      });

    return () => {
      controller.abort();
    };
  }, [activeTicketId, mergeTicketMessages, router]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;

    const inHumanMode =
      activeTicketId !== null && activeTicketStatus !== "resolved" && activeTicketStatus !== "closed";

    shouldStickToBottomRef.current = true;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);

    try {
      if (inHumanMode && activeTicketId) {
        await tickets.appendCustomerMessage(activeTicketId, text);
        setBackendOnline(true);
        return;
      }

      const assistantId = "assistant-stream-" + Date.now();
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "",
          localId: assistantId,
          model: selectedModel,
        },
      ]);

      let streamError: string | null = null;
      await chat.streamMessage(
        { query: text, model: selectedModel },
        ({ type, payload }) => {
          setBackendOnline(true);

          if (type === "chat.started") {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.localId === assistantId
                  ? { ...msg, model: payload.model ?? selectedModel }
                  : msg,
              ),
            );
            return;
          }

          if (type === "chat.metadata") {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.localId === assistantId
                  ? {
                      ...msg,
                      intent: payload.intent,
                      model: payload.model ?? selectedModel,
                      sources: payload.sources,
                      ticket_id: payload.ticket_id,
                    }
                  : msg,
              ),
            );
            return;
          }

          if (type === "chat.delta" && typeof payload.delta === "string") {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.localId === assistantId
                  ? { ...msg, content: msg.content + payload.delta }
                  : msg,
              ),
            );
            return;
          }

          if (type === "chat.done") {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.localId === assistantId
                  ? {
                      ...msg,
                      content: payload.answer ?? msg.content,
                      intent: payload.intent,
                      model: payload.model ?? selectedModel,
                      sources: payload.sources,
                      ticket_id: payload.ticket_id,
                    }
                  : msg,
              ),
            );
            if (payload.ticket_id) {
              setActiveTicketId(payload.ticket_id);
              setActiveTicketStatus("open");
              void loadActiveTicket(payload.ticket_id);
            }
            return;
          }

          if (type === "chat.error") {
            streamError = payload.detail ?? "抱歉，我暂时无法处理您的请求，请稍后重试。";
            setMessages((prev) =>
              prev.map((msg) =>
                msg.localId === assistantId ? { ...msg, content: streamError ?? msg.content } : msg,
              ),
            );
          }
        },
      );

      if (streamError) {
        return;
      }
    } catch (error) {
      let content = "抱歉，我暂时无法处理您的请求，请稍后重试。";

      if (error instanceof ApiError) {
        if (error.status === 401) {
          auth.logout();
          content = "登录已失效，请重新登录后再发送消息。";
          router.replace("/login");
        } else if (error.status >= 500) {
          content = error.detail || "后端服务暂时不可用，请稍后重试。";
        } else {
          content = error.detail || content;
        }
      } else {
        setBackendOnline(false);
        content = "后端服务暂时不可用，请稍后重试。";
      }

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  const inHumanMode =
    activeTicketId !== null && activeTicketStatus !== "resolved" && activeTicketStatus !== "closed";

  return (
    <AppShell>
      <ScrollArea ref={scrollRef} onScroll={handleScroll} className="flex-1 px-4 py-4">
        <div className="mx-auto max-w-3xl space-y-4">
          {activeTicketId && (
            <div className="flex items-center gap-2 rounded-lg border border-primary/20 bg-primary/5 px-3 py-2 text-xs text-primary">
              <Headphones className="h-4 w-4 shrink-0" />
              <span>
                人工服务工单 #{activeTicketId} · {ticketStatusLabel[activeTicketStatus ?? "open"] ?? activeTicketStatus}
              </span>
            </div>
          )}

          {messages.map((msg, i) => (
            <div
              key={String(msg.ticketMessageId ?? msg.localId ?? "local-" + i)}
              className={"flex gap-3 " + (msg.role === "user" ? "flex-row-reverse" : "")}
            >
              <Avatar
                fallback={msg.role === "user" ? "U" : "AI"}
                alt={msg.role === "user" ? "用户" : "助手"}
                className={msg.role === "user" ? "bg-primary" : "bg-muted"}
              />

              <div className={"flex max-w-[80%] flex-col gap-1 " + (msg.role === "user" ? "items-end" : "")}>
                <div
                  className={
                    "rounded-2xl px-4 py-2.5 text-sm leading-relaxed " +
                    (msg.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-foreground")
                  }
                >
                  <MarkdownMessage content={msg.content} />
                </div>

                {msg.role === "assistant" && (msg.intent || msg.model || msg.ticket_id) && (
                  <div className="flex flex-wrap gap-1.5 px-1">
                    {msg.intent && (
                      <Badge
                        variant={intentColor[msg.intent] ?? "secondary"}
                        className="text-[10px]"
                      >
                        {intentLabel[msg.intent] ?? msg.intent}
                      </Badge>
                    )}
                    {msg.model && (
                      <Badge variant="outline" className="text-[10px] text-muted-foreground">
                        {msg.model}
                      </Badge>
                    )}
                    {msg.ticket_id && (
                      <Badge variant="warning" className="text-[10px]">
                        <Ticket className="mr-0.5 h-3 w-3" />
                        工单 #{msg.ticket_id}
                      </Badge>
                    )}
                  </div>
                )}

                {msg.role === "assistant" && msg.sources && msg.sources.length > 0 && (
                  <div className="w-full space-y-1.5 px-1 pt-1">
                    <div className="flex items-center gap-1 text-[11px] font-medium text-muted-foreground">
                      <FileText className="h-3 w-3" />
                      <span>参考来源</span>
                    </div>
                    <div className="space-y-1.5">
                      {msg.sources.slice(0, 3).map((s, j) => {
                        const title = getSourceTitle(s);
                        const snippet = getSourceSnippet(s);

                        return (
                          <div
                            key={String(s.id ?? j)}
                            className="rounded-lg border bg-background/70 px-2.5 py-2 text-[11px] text-muted-foreground"
                          >
                            <div className="flex items-center justify-between gap-2">
                              <span className="truncate font-medium text-foreground">{title}</span>
                              <Badge variant="outline" className="shrink-0 text-[10px]">
                                {(s.score * 100).toFixed(0)}%
                              </Badge>
                            </div>
                            {snippet && (
                              <p className="mt-1 max-h-10 overflow-hidden leading-relaxed">
                                {snippet}
                              </p>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex gap-3">
              <Avatar fallback="AI" alt="助手" className="bg-muted" />
              <div className="flex items-center gap-2 rounded-2xl bg-muted px-4 py-2.5">
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                <span className="text-sm text-muted-foreground">
                  {inHumanMode ? "发送给人工客服..." : "思考中..."}
                </span>
              </div>
            </div>
          )}

          {backendOnline === false && (
            <div className="flex items-center gap-2 rounded-lg bg-destructive/10 px-3 py-2 text-xs text-destructive">
              <AlertCircle className="h-4 w-4 shrink-0" />
              后端服务暂时不可用，请确认 Docker 后端容器已启动
            </div>
          )}
        </div>
      </ScrollArea>

      {showNewMessages && (
        <Button
          type="button"
          size="sm"
          variant="secondary"
          onClick={scrollToBottom}
          className="fixed bottom-20 left-1/2 z-20 -translate-x-1/2 rounded-full shadow-md"
        >
          查看新消息
        </Button>
      )}

      <div className="border-t bg-card px-4 py-3">
        <form
          onSubmit={handleSubmit}
          className="mx-auto flex max-w-3xl items-center gap-2"
        >
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            disabled={loading || inHumanMode}
            className="h-11 shrink-0 rounded-xl border border-muted-foreground/20 bg-background px-3 text-xs text-muted-foreground outline-none focus:border-primary"
            title={inHumanMode ? "人工接入期间无需选择模型" : "选择模型"}
          >
            {AVAILABLE_MODELS.map((m) => (
              <option key={m.value} value={m.value}>
                {m.label}
              </option>
            ))}
          </select>
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={inHumanMode ? "输入消息，发送给人工客服..." : "输入您的问题..."}
            disabled={loading}
            autoFocus
            className="h-11 rounded-xl border-muted-foreground/20 bg-background pl-4 pr-3"
          />
          <Button
            type="submit"
            size="icon"
            disabled={loading || !input.trim()}
            className="h-11 w-11 shrink-0 rounded-xl"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </form>
      </div>
    </AppShell>
  );
}
