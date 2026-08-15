"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { auth } from "@/lib/api";

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    if (!auth.isLoggedIn()) {
      router.replace("/login");
      return;
    }

    auth
      .getMe()
      .then((user) => {
        router.replace(user.role === "customer" ? "/chat" : "/tickets");
      })
      .catch(() => {
        auth.logout();
        router.replace("/login");
      });
  }, [router]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background text-sm text-muted-foreground">
      正在进入系统...
    </div>
  );
}
