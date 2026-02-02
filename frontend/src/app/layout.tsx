import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "RFP Sniper | Government Contract Automation",
  description:
    "AI-powered platform for finding, analyzing, and winning government contracts.",
  keywords: ["government contracts", "RFP", "proposal automation", "SAM.gov"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${GeistSans.variable} ${GeistMono.variable} font-sans min-h-screen`}
      >
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}

