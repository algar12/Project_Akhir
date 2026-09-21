import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { DashboardProvider } from "@/contexts/DashboardContext";

const inter = Inter({
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Unified Network Guard",
  description: "Enterprise Security Dashboard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className={`${inter.className} bg-[#0b0c10] text-[#f7fafc] m-0 p-0 overflow-hidden`}>
        <DashboardProvider>
          {children}
        </DashboardProvider>
      </body>
    </html>
  );
}
