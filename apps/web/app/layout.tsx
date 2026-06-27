import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PC Build Copilot",
  description: "Vietnamese-first PC build intent foundation for Phong Vu."
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi">
      <body>{children}</body>
    </html>
  );
}
