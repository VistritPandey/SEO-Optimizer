import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000",
  ),
  title: {
    default: "Your Optimiser — SEO that keeps up with your website",
    template: "%s · Your Optimiser",
  },
  description:
    "Your AI agent for ongoing SEO. Check website updates, fix confirmed search problems and verify the result while you keep building your business.",
  openGraph: {
    title: "Your Optimiser",
    description:
      "Your website evolves. Your SEO needs to keep up. Meet your AI agent for ongoing website care.",
    type: "website",
  },
};
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
