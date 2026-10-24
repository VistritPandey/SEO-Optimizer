import type { Metadata } from "next";
import { ThemeProvider } from "@/components/ThemeProvider";
import { NavigationScroll } from "@/components/NavigationScroll";
import { DM_Sans, DM_Serif_Display } from "next/font/google";
import { site } from "@/lib/site";
import "./globals.css";

const sans = DM_Sans({
  subsets: ["latin"],
  display: "optional",
  variable: "--font-sans",
});
const serif = DM_Serif_Display({
  weight: "400",
  style: ["normal", "italic"],
  subsets: ["latin"],
  display: "optional",
  variable: "--font-serif",
});

export const metadata: Metadata = {
  metadataBase: new URL(site.url),
  title: {
    default: "Your Optimiser - Your autonomous SEO agent",
    template: "%s · Your Optimiser",
  },
  description: site.description,
  applicationName: site.name,
  category: "business",
  openGraph: {
    url: site.url,
    title: "Your Optimiser",
    description:
      "Your autonomous SEO agent. Website checks, focused GitHub fixes and verification after deployment.",
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
    <html
      lang="en"
      data-scroll-behavior="smooth"
      className={`${sans.variable} ${serif.variable}`}
      suppressHydrationWarning
    >
      <head>
        <script
          id="theme-initialization"
          dangerouslySetInnerHTML={{
            __html: `(function(){var t='system';try{var s=localStorage.getItem('optimiser-theme');if(s==='light'||s==='dark')t=s;}catch(e){}document.documentElement.dataset.theme=t==='system'?(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'):t;})();`,
          }}
        />
      </head>
      {/* Writing extensions may attach data-gr-* attributes before hydration.
          Tolerate body attributes only; descendants keep React's checks. */}
      <body suppressHydrationWarning>
        <a href="#main-content" className="skip-link">
          Skip to content
        </a>
        <ThemeProvider>
          {children}
          <NavigationScroll />
        </ThemeProvider>
      </body>
    </html>
  );
}
