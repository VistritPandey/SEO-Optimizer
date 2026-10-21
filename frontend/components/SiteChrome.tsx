import Link from "next/link";
import { Brand } from "./Brand";

export { SiteHeader } from "./SiteHeader";

export function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="footer-top">
        <div>
          <Brand />
          <p>
            Your autonomous SEO agent.
            <br />
            Always watching. Ready to help.
          </p>
        </div>
        <nav aria-label="Product links">
          <span>THE PRODUCT</span>
          <Link href="/how-it-works">How it works</Link>
          <Link href="/seo-and-ai-search">SEO & AI search</Link>
          <Link href="/#pricing">Free plan</Link>
          <Link href="/blog">Blog & guides</Link>
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
