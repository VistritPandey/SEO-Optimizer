import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000",
  ),
  title: {
    default: "Your Optimiser — A working partner for your website",
    template: "%s · Your Optimiser",
  },
  description:
    "Find search problems, make evidence-backed improvements, and verify the result. SEO and AI discovery, connected to your repository.",
  openGraph: {
    title: "Your Optimiser",
    description:
      "Evidence before action. A clearer path to a discoverable website.",
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
