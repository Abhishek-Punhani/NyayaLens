import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NyayaLens — Legal Voice Intelligence",
  description: "Production voice-first legal intake and adversarial analysis for Indian property disputes",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:ital,wght@0,400;0,500;1,400&family=Space+Mono:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet" />
      </head>
      <body className="bg-[#0b0d0e] text-[#e1e2e3] font-['Space_Mono'] min-h-screen antialiased">
        {children}
      </body>
    </html>
  );
}
