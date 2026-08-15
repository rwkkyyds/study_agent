import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  turbopack: {
    root: __dirname,
  },
  // 关闭 Next.js 内置开发工具面板（左下角的"N"按钮），
  // 避免与项目 UI 产生干扰，且该面板不支持中文
  devIndicators: false,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/:path*",
      },
    ];
  },
};

export default nextConfig;