import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "智能学业规划",
  description: "智能学业规划与课表优化本地界面",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
