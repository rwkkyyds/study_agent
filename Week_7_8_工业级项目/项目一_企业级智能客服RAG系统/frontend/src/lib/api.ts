/**
 * 后端 API 客户端
 *
 * 封装所有后端接口调用，自动管理 JWT Token 的 localStorage 存取，
 * 统一处理请求错误与网络异常。
 */

// ─── 类型定义（与后端 Pydantic Schema 对齐） ─────────────────────────

export interface RegisterRequest {
  username: string;
  password: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserResponse {
  id: number;
  username: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface ChatRequest {
  query: string;
  model?: string;
}

export interface SourceItem {
  id: string;
  score: number;
  metadata: Record<string, unknown>;
  content?: string | null;
}

export interface ChatResponse {
  answer: string;
  intent: string;
  model?: string | null;
  sources: SourceItem[];
  ticket_id?: number | null;
  order?: Record<string, unknown> | null;
}

export interface ChatStreamEvent {
  type: "chat.started" | "chat.metadata" | "chat.delta" | "chat.done" | "chat.error" | string;
  payload: Partial<ChatResponse> & {
    delta?: string;
    detail?: string;
    error?: string;
  };
}

export interface TicketResponse {
  id: number;
  title: string;
  description: string;
  status: string;
  priority: string;
  customer_id: number;
  agent_id?: number | null;
  created_at: string;
  updated_at: string;
  messages?: TicketMessage[];
}

export interface TicketMessage {
  id: number;
  ticket_id: number;
  sender_id: number;
  sender_role: string;
  content: string;
  msg_type: string;
  created_at: string;
}

export interface TicketStreamEvent {
  type: "ticket.snapshot" | "ticket.updated" | string;
  ticket: TicketResponse;
}

export interface TicketListStreamEvent {
  type: "ticket.created" | "ticket.updated" | string;
  ticket: TicketResponse;
}

export interface HealthResponse {
  status: string;
  environment: string;
}

export interface DocumentItem {
  id: number;
  title: string;
  source: string;
  chunk_count: number;
  created_at: string;
}

export interface DocumentUploadResponse {
  id: number;
  title: string;
  chunks: number;
  message: string;
}

export interface CreateUserRequest {
  username: string;
  password: string;
  role: string;
}

// ─── API 错误类 ──────────────────────────────────────────────────

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

// ─── Token 管理 ──────────────────────────────────────────────────

const TOKEN_KEY = "access_token";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
  // 同步设置 cookie 供 middleware 路由守卫使用
  document.cookie = `${TOKEN_KEY}=${token}; path=/; max-age=86400; SameSite=Lax`;
}

function removeToken(): void {
  localStorage.removeItem(TOKEN_KEY);
  // 清除 cookie
  document.cookie = `${TOKEN_KEY}=; path=/; max-age=0; SameSite=Lax`;
}

// ─── HTTP 基础请求 ───────────────────────────────────────────────

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };

  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let detail = `请求失败 (${response.status})`;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      // 非 JSON 响应体，使用默认错误信息
    }
    throw new ApiError(response.status, detail);
  }

  // 204 No Content
  if (response.status === 204) {
    return undefined as unknown as T;
  }

  return response.json() as Promise<T>;
}

function parseSseMessage(raw: string): { event: string; data: string } | null {
  let event = "message";
  const dataLines: string[] = [];

  for (const line of raw.split(/\r?\n/)) {
    if (!line || line.startsWith(":")) continue;
    if (line.startsWith("event:")) {
      event = line.slice("event:".length).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trimStart());
    }
  }

  if (dataLines.length === 0) return null;
  return { event, data: dataLines.join("\n") };
}

async function streamSse(
  endpoint: string,
  options: RequestInit = {},
  onEvent: (event: { type: string; payload: unknown }) => void,
  signal?: AbortSignal,
): Promise<void> {
  const headers: Record<string, string> = {
    Accept: "text/event-stream",
    ...(options.body ? { "Content-Type": "application/json" } : {}),
    ...(options.headers as Record<string, string> | undefined),
  };

  const token = getToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
    signal,
  });

  if (!response.ok) {
    let detail = `请求失败 (${response.status})`;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      // SSE 失败时可能没有 JSON 响应体。
    }
    throw new ApiError(response.status, detail);
  }

  if (!response.body) {
    throw new ApiError(response.status, "浏览器不支持流式响应");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const chunks = buffer.split(/\n\n|\r\n\r\n/);
      buffer = chunks.pop() ?? "";

      for (const chunk of chunks) {
        const parsed = parseSseMessage(chunk);
        if (!parsed) continue;
        onEvent({
          type: parsed.event,
          payload: JSON.parse(parsed.data) as unknown,
        });
      }
    }
  } finally {
    reader.releaseLock();
  }
}

// ─── Auth API ─────────────────────────────────────────────────────

export const auth = {
  /** 注册新用户 */
  async register(data: RegisterRequest): Promise<UserResponse> {
    return request<UserResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  /** 登录并自动保存 Token */
  async login(data: LoginRequest): Promise<TokenResponse> {
    const result = await request<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify(data),
    });
    setToken(result.access_token);
    return result;
  },

  /** 获取当前登录用户信息 */
  async getMe(): Promise<UserResponse> {
    return request<UserResponse>("/auth/me");
  },

  /** 登出（清除本地 Token） */
  logout(): void {
    removeToken();
  },

  /** 检查是否已登录（本地 Token 是否存在） */
  isLoggedIn(): boolean {
    return getToken() !== null;
  },
};

// ─── Chat API ─────────────────────────────────────────────────────

export const chat = {
  /** 发送客服对话消息 */
  async sendMessage(data: ChatRequest): Promise<ChatResponse> {
    return request<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  /** 发送客服对话消息并通过 SSE 流式接收回复 */
  async streamMessage(
    data: ChatRequest,
    onEvent: (event: ChatStreamEvent) => void,
    signal?: AbortSignal,
  ): Promise<void> {
    return streamSse(
      "/chat/stream",
      {
        method: "POST",
        body: JSON.stringify(data),
      },
      (event) =>
        onEvent({
          type: event.type,
          payload: event.payload as ChatStreamEvent["payload"],
        }),
      signal,
    );
  },
};

// ─── Tickets API ──────────────────────────────────────────────────

export const tickets = {
  /** 获取当前用户的工单列表 */
  async listTickets(): Promise<TicketResponse[]> {
    return request<TicketResponse[]>("/tickets");
  },

  /** 获取单个工单详情 */
  async getTicket(id: number): Promise<TicketResponse> {
    return request<TicketResponse>(`/tickets/${id}`);
  },

  /** 用户在已转人工的会话中继续发送消息 */
  async appendCustomerMessage(id: number, content: string): Promise<TicketResponse> {
    return request<TicketResponse>(`/tickets/${id}/messages`, {
      method: "POST",
      body: JSON.stringify({ content }),
    });
  },

  /** 客服领取 open 工单 */
  async claimTicket(id: number): Promise<TicketResponse> {
    return request<TicketResponse>(`/tickets/${id}/claim`, {
      method: "POST",
    });
  },

  /** 客服回复工单 */
  async replyTicket(id: number, content: string): Promise<TicketResponse> {
    return request<TicketResponse>(`/tickets/${id}/reply`, {
      method: "POST",
      body: JSON.stringify({ content }),
    });
  },

  /** 订阅单个工单的 SSE 消息流 */
  async streamTicketEvents(
    id: number,
    onEvent: (event: TicketStreamEvent) => void,
    signal?: AbortSignal,
  ): Promise<void> {
    return streamSse(
      `/tickets/${id}/events`,
      {},
      (event) =>
        onEvent({
          type: event.type,
          ticket: event.payload as TicketResponse,
        }),
      signal,
    );
  },

  /** 订阅当前用户可见工单列表的 SSE 消息流 */
  async streamTicketListEvents(
    onEvent: (event: TicketListStreamEvent) => void,
    signal?: AbortSignal,
  ): Promise<void> {
    return streamSse(
      "/tickets/events",
      {},
      (event) =>
        onEvent({
          type: event.type,
          ticket: event.payload as TicketResponse,
        }),
      signal,
    );
  },

  /** 客服标记工单已解决 */
  async resolveTicket(id: number): Promise<TicketResponse> {
    return request<TicketResponse>(`/tickets/${id}/resolve`, {
      method: "POST",
    });
  },

  /** 客服关闭已解决工单 */
  async closeTicket(id: number): Promise<TicketResponse> {
    return request<TicketResponse>(`/tickets/${id}/close`, {
      method: "POST",
    });
  },
};

// ─── Health API ───────────────────────────────────────────────────

export const health = {
  /** 检查后端服务健康状态 */
  async checkHealth(): Promise<HealthResponse> {
    return request<HealthResponse>("/health");
  },
};

// ─── Documents API（知识库）───────────────────────────────────────

export const documents = {
  /** 获取知识库文档列表 */
  async listDocuments(): Promise<DocumentItem[]> {
    return request<DocumentItem[]>("/documents");
  },

  /** 上传文档（后端以 query 参数接收 title/content/source） */
  async uploadDocument(
    title: string,
    content: string,
    source = "manual",
  ): Promise<DocumentUploadResponse> {
    const params = new URLSearchParams({ title, content, source });
    return request<DocumentUploadResponse>(`/documents/upload?${params.toString()}`, {
      method: "POST",
    });
  },

  /** 删除文档（仅 admin） */
  async deleteDocument(id: number): Promise<void> {
    return request<void>(`/documents/${id}`, { method: "DELETE" });
  },
};

// ─── Admin API（管理员）───────────────────────────────────────────

export const admin = {
  /** 获取全部用户列表（仅 admin） */
  async listUsers(): Promise<UserResponse[]> {
    return request<UserResponse[]>("/auth/users");
  },

  /** 创建用户，可指定角色（仅 admin） */
  async createUser(data: CreateUserRequest): Promise<UserResponse> {
    return request<UserResponse>("/auth/users", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },
};
