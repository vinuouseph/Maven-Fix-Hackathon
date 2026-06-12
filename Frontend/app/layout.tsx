import type { Metadata } from 'next';
import '../styles/globals.css';

export const metadata: Metadata = {
  title: 'MavenFix AI — Automated Maven Repair Platform',
  description:
    'MavenFix uses an advanced LangGraph AI pipeline to automatically detect and fix compilation errors in your Maven projects. Connect your Git repo, sit back, and let the AI do the work.',
  keywords: 'Maven, AI, automated fix, LangGraph, compiler errors',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
