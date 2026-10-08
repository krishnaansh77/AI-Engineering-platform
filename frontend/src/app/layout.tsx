import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { GitBranch, MessageSquare, LayoutDashboard, BookOpen } from "lucide-react";

export const metadata: Metadata = {
  title: "AI Software Engineering Intelligence Platform",
  description:
    "AI-powered platform to understand, navigate, and analyze software repositories.",
};

const navLinks = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/repos/new", label: "Connect Repo", icon: GitBranch },
  { href: "/docs", label: "Documentation", icon: BookOpen },
];

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="flex h-screen bg-slate-50 overflow-hidden">
        {/* Sidebar */}
        <aside className="w-64 flex-shrink-0 bg-slate-900 flex flex-col border-r border-slate-800">
          {/* Logo */}
          <div className="px-5 py-5 border-b border-slate-800">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-sky-500 flex items-center justify-center flex-shrink-0">
                <MessageSquare className="w-4 h-4 text-white" />
              </div>
              <div>
                <p className="text-white font-semibold text-sm leading-tight">
                  AISE Platform
                </p>
                <p className="text-slate-400 text-xs">
                  AI Code Intelligence
                </p>
              </div>
            </div>
          </div>

          {/* Nav */}
          <nav className="flex-1 px-3 py-4 space-y-1">
            {navLinks.map(({ href, label, icon: Icon }) => (
              <Link
                key={href}
                href={href}
                className="flex items-center gap-3 px-3 py-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 text-sm font-medium group"
              >
                <Icon className="w-4 h-4 group-hover:text-sky-400" />
                {label}
              </Link>
            ))}
          </nav>

          {/* Footer */}
          <div className="px-5 py-4 border-t border-slate-800">
            <p className="text-slate-500 text-xs">Phase 3 · Developer Productivity &amp; Safety</p>
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1 overflow-auto">{children}</main>
      </body>
    </html>
  );
}
