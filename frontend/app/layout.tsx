import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { Toaster } from "./components/ui/toaster"
import { Toaster as HotToaster } from "react-hot-toast"
import { ThemeProvider } from "./contexts/ThemeContext"

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'ThinkForge',
  description: 'A web application for managing chain of thought templates',
  icons: {
    icon: { url: '/icon.svg', type: 'image/svg+xml' },
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <ThemeProvider>
          {children}
          <Toaster />
          <HotToaster 
            position="top-right"
            toastOptions={{
              duration: 3000,
              style: {
                background: 'hsl(var(--card))',
                color: 'hsl(var(--card-foreground))',
                border: '1px solid hsl(var(--border))',
              },
              success: {
                iconTheme: {
                  primary: '#10B981',
                  secondary: 'hsl(var(--card-foreground))',
                },
              },
              error: {
                iconTheme: {
                  primary: '#EF4444',
                  secondary: 'hsl(var(--card-foreground))',
                },
              },
            }}
          />
        </ThemeProvider>
      </body>
    </html>
  )
} 