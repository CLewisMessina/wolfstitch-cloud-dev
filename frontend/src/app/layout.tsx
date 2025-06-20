import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Wolfstitch - AI Dataset Preparation Platform",
  description: "Transform documents into AI-ready datasets with intelligent chunking and 40+ file formats support",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-dark min-h-screen text-white antialiased`}>
        {children}
      </body>
    </html>
  );
}