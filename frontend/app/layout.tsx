import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DocTagger - AI-Powered PDF Organization",
  description: "Automatically tag and organize PDF documents using local LLM",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
