import type { NextConfig } from "next";
const nextConfig: NextConfig = {
  output: "export",
  transpilePackages: ["@sapsos/shared"],
};
export default nextConfig;
