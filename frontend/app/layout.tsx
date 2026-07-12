import type { Metadata } from 'next'
import type { } from './globals.css'
import React from 'react'

export const metadata: Metadata = {
  title: 'MeetingGhost',
  description: 'Offline meeting intelligence'
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen bg-gray-50">
          <header className="p-4 shadow-sm bg-white">
            <h1 className="text-xl font-semibold">MeetingGhost</h1>
          </header>
          <main className="p-6">{children}</main>
        </div>
      </body>
    </html>
  )
}
