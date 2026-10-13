import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Chốt — biên bản họp có bằng chứng",
  description: "Biến transcript cuộc họp thành quyết định, công việc và việc còn treo — mỗi dòng trỏ về câu nói gốc.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap"
        />
      </head>
      <body>
        <header className="topbar">
          <Link href="/" className="brand">
            <span className="brand-seal" aria-hidden>
              C
            </span>
            Chốt
          </Link>
          <span className="faint">Biên bản họp có bằng chứng</span>
        </header>
        <main className="container">{children}</main>
      </body>
    </html>
  );
}
