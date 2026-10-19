import type { Metadata } from "next";
import { DM_Sans, DM_Serif_Display } from "next/font/google";
import { MotionProvider } from "@/components/Motion";
import { site } from "@/lib/site";
import "./globals.css";

const sans = DM_Sans({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-sans",
});
const serif = DM_Serif_Display({
  weight: "400",
  style: ["normal", "italic"],
  subsets: ["latin"],
  display: "swap",
  variable: "--font-serif",
});

export const metadata: Metadata = {
  metadataBase: new URL(site.url),
  title: {
    default: "Your Optimiser — SEO that keeps up with your website",
    template: "%s · Your Optimiser",
  },
  description: site.description,
  applicationName: site.name,
  category: "business",
  openGraph: {
    url: site.url,
    title: "Your Optimiser",
    description:
      "Your website evolves. Your SEO needs to keep up. Meet your AI agent for ongoing website care.",
    type: "website",
    siteName: site.name,
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    title: site.name,
    description: site.description,
  },
  robots: {
    index: true,
    follow: true,
    googleBot: { index: true, follow: true, "max-image-preview": "large" },
  },
  other: { "theme-color": "#f7f7f0" },
};
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${sans.variable} ${serif.variable}`}>
      <body>
        <a href="#main-content" className="skip-link">
          Skip to content
        </a>
        <MotionProvider>{children}</MotionProvider>
      </body>
    </html>
  );
}
