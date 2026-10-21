import Image from "next/image";
import Link from "next/link";
import { ArticleCards } from "@/components/ArticleCards";
import { SiteHeader, SiteFooter } from "@/components/SiteChrome";
import { pageMetadata, site } from "@/lib/site";
import { articles } from "@/lib/articles";

export const metadata = pageMetadata(
  "The SEO journal",
  "Practical articles on autonomous SEO agents, website release checks and AI-search visibility. Clear methods, original examples and evidence you can inspect.",
  "/blog",
);

export default function Page() {
  const schema = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    name: "The Your Optimiser journal",
    url: `${site.url}/blog`,
    mainEntity: {
      "@type": "ItemList",
      itemListElement: articles.map((article, index) => ({
        "@type": "ListItem",
        position: index + 1,
        name: article.title,
        url: `${site.url}/blog/${article.slug}`,
      })),
    },
  };
  return (
    <>
      <SiteHeader />
      <main id="main-content" className="journal-page">
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify(schema).replace(/</g, "\\u003c"),
          }}
        />
        <header className="journal-heading">
          <span className="eyebrow">THE YOUR OPTIMISER JOURNAL</span>
          <h1>
            Keep your website moving.
            <br />
            <em>Keep learning as you go.</em>
          </h1>
          <p>
            Practical notes on autonomous SEO, better website updates and being
            understood in search. Written around real workflows, with the
            evidence and limits in view.
          </p>
        </header>
        <ArticleCards />
        <section className="journal-guide" aria-labelledby="field-guide-title">
          <Image
            src="/editorial/clear-discovery.webp"
            alt="Layered ivory paper opening onto a green path."
            width={1440}
            height={960}
            sizes="(max-width: 760px) 88vw, 40vw"
          />
          <div>
            <span className="eyebrow">THE FIELD GUIDE</span>
            <h2 id="field-guide-title">
              A practical process for SEO that keeps going.
            </h2>
            <p>
              Set a baseline. Follow relevant changes. Establish evidence.
              Review a focused repair. Verify the live page. Our longer guide
              connects the steps.
            </p>
            <Link href="/guides/continuous-seo" className="text-link">
              Read the continuous SEO guide →
            </Link>
          </div>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
