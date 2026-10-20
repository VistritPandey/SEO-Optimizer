import Link from "next/link";
import { Brand } from "./Brand";
import { ThemeControl } from "./ThemeControl";
import { site } from "@/lib/site";

export function SiteHeader() {
  return (
    <header className="marketing-nav">
      <Brand />
      <nav aria-label="Main navigation">
        <Link href="/how-it-works">How it works</Link>
        <Link href="/seo-and-ai-search">What we look after</Link>
        <Link href="/#pricing">Pricing</Link>
        <a
          className="nav-github"
          href={site.repository}
          target="_blank"
          rel="noopener noreferrer"
          aria-label="Your Optimiser on GitHub (opens in a new tab)"
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="currentColor"
            aria-hidden="true"
          >
            <path d="M12 .9a11.1 11.1 0 0 0-3.51 21.63c.55.1.76-.24.76-.54v-2.07c-3.1.67-3.76-1.32-3.76-1.32-.5-1.28-1.24-1.62-1.24-1.62-1.01-.69.08-.68.08-.68 1.12.08 1.71 1.15 1.71 1.15.99 1.7 2.59 1.21 3.22.92.1-.72.38-1.21.71-1.49-2.48-.28-5.08-1.24-5.08-5.52 0-1.22.43-2.22 1.14-3-.11-.28-.49-1.42.11-2.96 0 0 .93-.3 3.05 1.14a10.6 10.6 0 0 1 5.55 0c2.12-1.44 3.05-1.14 3.05-1.14.6 1.54.22 2.68.11 2.96.71.78 1.14 1.78 1.14 3 0 4.29-2.61 5.24-5.1 5.51.4.35.76 1.02.76 2.06v3.06c0 .3.2.65.77.54A11.1 11.1 0 0 0 12 .9Z" />
          </svg>
          <span>GitHub</span>
        </a>
        <Link className="nav-signin" href="/dashboard">
          Your workspace ↗
        </Link>
      </nav>
      <ThemeControl compact />
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="footer-top">
        <div>
          <Brand />
          <p>
            A little care for everything
            <br />
            you’re building online.
          </p>
        </div>
        <nav aria-label="Product links">
          <span>THE PRODUCT</span>
          <Link href="/how-it-works">How it works</Link>
          <Link href="/seo-and-ai-search">SEO & AI search</Link>
          <Link href="/#pricing">Free plan</Link>
          <Link href="/guides/continuous-seo">The ongoing SEO guide</Link>
        </nav>
        <nav aria-label="Company and policies">
          <span>GOOD TO KNOW</span>
          <Link href="/security">Security & control</Link>
          <Link href="/contact">Get in touch</Link>
          <Link href="/privacy">Privacy</Link>
          <Link href="/terms">Terms</Link>
        </nav>
      </div>
      <div className="footer-bottom">
        <span>© {new Date().getFullYear()} Your Optimiser</span>
        <span>Built for the website you’re still building.</span>
        <a href="/llms.txt">Product facts for AI readers ↗</a>
      </div>
    </footer>
  );
}
