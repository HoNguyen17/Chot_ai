import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // "standalone" cho Docker; Vercel tự bỏ qua tuỳ chọn này.
  output: "standalone",
};

export default nextConfig;
