import type { Metadata } from "next"
import "./globals.css"

export const metadata: Metadata = {
  title: "Sarvam Voice Translator",
  description: "Real-time voice translation across 22 Indian languages, powered by Sarvam AI",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-sarvam-dark antialiased">
        {children}
      </body>
    </html>
  )
}
