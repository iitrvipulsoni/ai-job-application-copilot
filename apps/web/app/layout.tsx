import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'AI Job Application Copilot',
  description: 'Tailor job applications truthfully, manage resumes, and track interviews.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        <nav className="navbar">
          <div className="container nav-container">
            <div className="logo">
              <span style={{ fontSize: '1.8rem' }}>🛡️</span>
              <span>Job Copilot</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1.2rem' }}>
              <span className="badge badge-applied" style={{ textTransform: 'none', fontWeight: 600, fontSize: '0.8rem' }}>
                🟢 Sprint 1 Developer Sandbox
              </span>
            </div>
          </div>
        </nav>
        <main className="container" style={{ paddingBottom: '5rem' }}>
          {children}
        </main>
      </body>
    </html>
  )
}
