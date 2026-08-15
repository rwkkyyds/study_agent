"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { auth, documents, DocumentItem } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import AppShell from "@/components/app-shell";
import {
  BookOpen,
  Upload,
  Trash2,
  Loader2,
  AlertCircle,
  CheckCircle2,
  FileText,
  Clock,
} from "lucide-react";

export default function DocumentsPage() {
  const router = useRouter();
  const [role, setRole] = useState("");
  const [docList, setDocList] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // 上传表单状态
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [source, setSource] = useState("manual");
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState("");
  const [uploadErr, setUploadErr] = useState("");

  const loadDocs = useCallback(async () => {
    setLoading(true);
    try {
      const list = await documents.listDocuments();
      setDocList(list);
      setError("");
    } catch {
      setError("无法加载文档列表");
    } finally {
      setLoading(false);
    }
  }, []);

  // 检查登录状态并获取角色
  useEffect(() => {
    if (!auth.isLoggedIn()) {
      router.push("/login");
      return;
    }
    auth.getMe()
      .then((u) => {
        if (u.role === "customer") {
          router.replace("/chat");
          return;
        }
        setRole(u.role);
        void loadDocs();
      })
      .catch(() => {
        auth.logout();
        router.replace("/login");
      });
  }, [loadDocs, router]);

  async function handleUpload() {
    if (role !== "admin") {
      setUploadErr("只有管理员可以录入知识库");
      return;
    }
    if (!title.trim() || !content.trim()) {
      setUploadErr("标题和内容不能为空");
      return;
    }
    setUploading(true);
    setUploadErr("");
    setUploadMsg("");
    try {
      const res = await documents.uploadDocument(title.trim(), content.trim(), source.trim() || "manual");
      setUploadMsg(`上传成功：${res.title}（切分 ${res.chunks} 块）`);
      setTitle("");
      setContent("");
      await loadDocs();
    } catch (e) {
      setUploadErr(e instanceof Error ? e.message : "上传失败");
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(id: number) {
    if (!window.confirm("确认删除该文档？知识库中的相关内容将不可再被检索。")) {
      return;
    }
    try {
      await documents.deleteDocument(id);
      await loadDocs();
    } catch (e) {
      setError(e instanceof Error ? e.message : "删除失败");
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

  const isAdmin = role === "admin";

  return (
    <AppShell>
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* 顶部标题栏 */}
        <div className="flex h-12 shrink-0 items-center justify-between border-b bg-card px-4">
          <div className="flex items-center gap-2">
            <BookOpen className="h-5 w-5 text-primary" />
            <h1 className="text-sm font-semibold">知识库</h1>
          </div>
          <Badge variant="secondary" className="text-xs">
            共 {docList.length} 篇文档
          </Badge>
        </div>

        <ScrollArea className="flex-1 p-4">
          <div className="mx-auto max-w-2xl space-y-4">
            {/* 上传表单：仅管理员可见 */}
            {isAdmin ? (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Upload className="h-4 w-4" />
                    录入文档
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="grid gap-3 sm:grid-cols-[1fr_160px]">
                    <div className="space-y-1.5">
                      <label className="text-xs text-muted-foreground">标题</label>
                      <Input
                        placeholder="例如：退款规则"
                        value={title}
                        onChange={(e) => setTitle(e.target.value)}
                      />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-xs text-muted-foreground">来源（可选）</label>
                      <Input
                        placeholder="manual"
                        value={source}
                        onChange={(e) => setSource(e.target.value)}
                      />
                    </div>
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs text-muted-foreground">内容</label>
                    <Textarea
                      placeholder="粘贴知识库文档内容，系统会自动切分并建立检索索引…"
                      value={content}
                      onChange={(e) => setContent(e.target.value)}
                      rows={5}
                    />
                  </div>

                  {uploadMsg && (
                    <p className="flex items-center gap-1.5 text-xs text-emerald-600 dark:text-emerald-400">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      {uploadMsg}
                    </p>
                  )}
                  {uploadErr && (
                    <p className="flex items-center gap-1.5 text-xs text-destructive">
                      <AlertCircle className="h-3.5 w-3.5" />
                      {uploadErr}
                    </p>
                  )}

                  <Button
                    onClick={handleUpload}
                    disabled={uploading || !title.trim() || !content.trim()}
                    className="gap-1.5"
                    size="sm"
                  >
                    {uploading ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Upload className="h-3.5 w-3.5" />
                    )}
                    {uploading ? "上传中…" : "上传并索引"}
                  </Button>
                </CardContent>
              </Card>
            ) : (
              <Card>
                <CardContent className="p-4 text-xs text-muted-foreground">
                  当前为客服只读模式：可查看知识库文档，录入和删除仅管理员可执行。
                </CardContent>
              </Card>
            )}

            {/* 文档列表 */}
            {loading ? (
              <div className="flex justify-center py-10">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : error && docList.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <AlertCircle className="mb-3 h-10 w-10 text-destructive" />
                <p className="text-sm text-muted-foreground">{error}</p>
              </div>
            ) : docList.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <FileText className="mb-3 h-12 w-12 text-muted-foreground/40" />
                <p className="text-sm text-muted-foreground">知识库还是空的</p>
                <p className="mt-1 text-xs text-muted-foreground/60">
                  在上方录入第一份文档，客服问答就能检索到它
                </p>
              </div>
            ) : (
              <div className="space-y-2.5">
                {docList.map((doc) => (
                  <Card key={doc.id} className="transition-all hover:shadow-md">
                    <CardContent className="flex items-center gap-3 p-3.5">
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                        <FileText className="h-4 w-4 text-primary" />
                      </div>
                      <div className="min-w-0 flex-1 space-y-0.5">
                        <div className="flex items-center gap-2">
                          <span className="truncate text-sm font-medium">{doc.title}</span>
                          <Badge variant="secondary" className="shrink-0 text-[10px]">
                            {doc.chunk_count} 块
                          </Badge>
                        </div>
                        <p className="flex items-center gap-1 text-[10px] text-muted-foreground">
                          <Clock className="h-3 w-3" />
                          {formatDate(doc.created_at)}
                          {doc.source && doc.source !== "manual" && ` · 来源：${doc.source}`}
                        </p>
                      </div>
                      {isAdmin && (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDelete(doc.id)}
                          title="删除文档（仅管理员）"
                          className="shrink-0 text-muted-foreground hover:text-destructive"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      )}
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
