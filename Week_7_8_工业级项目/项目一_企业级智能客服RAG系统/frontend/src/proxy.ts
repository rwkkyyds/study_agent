import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const TOKEN_KEY = "access_token";

// 需要登录才能访问的路由
const PROTECTED_ROUTES = ["/chat", "/tickets", "/documents", "/admin"];

// 已登录用户访问时跳转到 /chat 的路由
const AUTH_ROUTES = ["/login", "/register"];

export default function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const token = request.cookies.get(TOKEN_KEY)?.value;

  // 访问受保护路由但未登录 → 重定向到 /login
  if (PROTECTED_ROUTES.some((route) => pathname.startsWith(route))) {
    if (!token) {
      const loginUrl = new URL("/login", request.url);
      loginUrl.searchParams.set("redirect", pathname);
      return NextResponse.redirect(loginUrl);
    }
  }

  // 已登录用户访问登录/注册页 → 重定向到 /chat
  if (AUTH_ROUTES.some((route) => pathname.startsWith(route))) {
    if (token) {
      return NextResponse.redirect(new URL("/chat", request.url));
    }
  }

return NextResponse.next();
}

export const config = {
  matcher: [
    // 匹配需要保护的路由，排除静态资源、API 代理、_next 内部路由
    "/((?!api/|_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};