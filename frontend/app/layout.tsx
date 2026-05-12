import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Meeting Assistant",
  description: "Create, process, and export structured meeting notes.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="app-shell">
          <header className="topbar">
            <div className="topbar-inner">
              <Link className="brand" href="/">
                <span className="brand-mark" aria-hidden="true">
                  M
                </span>
                <span className="brand-copy">
                  <span>Meeting Assistant</span>
                  <small>AI notes workspace</small>
                </span>
              </Link>
              <nav className="nav" aria-label="Primary navigation">
                <Link className="nav-link" href="/meetings">
                  Meetings
                </Link>
                <Link className="nav-link" href="/meetings/new">
                  New
                </Link>
                <Link className="nav-link" href="/settings">
                  Settings
                </Link>
              </nav>
            </div>
          </header>
          {children}
        </div>
      </body>
    </html>
  );
}
