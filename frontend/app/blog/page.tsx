import Image from "next/image";
import Link from "next/link";
import { ArticleCards } from "@/components/ArticleCards";
import { SiteHeader, SiteFooter } from "@/components/SiteChrome";
import { pageMetadata, site } from "@/lib/site";
import { articles, continuousSeoGuideCover } from "@/lib/articles";

export const metadata = pageMetadata(
  "SEO & GEO Blog",
  "The Your Optimiser Blog: practical SEO and GEO guides, autonomous agent workflows and website release checklists, with original examples and clear evidence.",
  "/blog",
);

export default function Page() {
  const schema = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    "@id": `${site.url}/blog#webpage`,
    name: "Your Optimiser Blog",
    url: `${site.url}/blog`,
    isPartOf: {
      "@type": "WebSite",
      "@id": `${site.url}/#website`,
      name: site.name,
      url: site.url,
    },
    publisher: {
      "@type": "Organization",
      "@id": `${site.url}/#organization`,
      name: site.name,
      url: site.url,
    },
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
          <span className="eyebrow">THE YOUR OPTIMISER BLOG</span>
          <h1>
            Practical SEO.
            <br />
            <em>Clearer AI visibility.</em>
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
            src={continuousSeoGuideCover.image}
            alt={continuousSeoGuideCover.imageAlt}
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
