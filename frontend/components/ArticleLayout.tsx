import Image from "next/image";
import Link from "next/link";
import type { ReactNode } from "react";
import { SiteFooter, SiteHeader } from "./SiteChrome";
import { site } from "@/lib/site";

export function ArticleLayout({
  title, description, category, path, published, updated, minutes, image, imageAlt,
  takeaway, contents, children,
}: {
  title: string; description: string; category: string; path: string;
  published: string; updated?: string; minutes: number; image: string; imageAlt: string;
  takeaway: string; contents: { id: string; title: string }[]; children: ReactNode;
}) {
  const graph = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "BlogPosting", "@id": `${site.url}${path}#article`,
        headline: title, description, image: `${site.url}${image}`,
        datePublished: published, dateModified: updated ?? published,
        author: { "@type": "Organization", name: site.name, url: site.url },
        publisher: { "@type": "Organization", name: site.name, url: site.url,
          logo: { "@type": "ImageObject", url: `${site.url}/brand/logo.png` } },
        mainEntityOfPage: `${site.url}${path}`, inLanguage: "en",
      },
      {
        "@type": "BreadcrumbList", itemListElement: [
          { "@type": "ListItem", position: 1, name: "Home", item: site.url },
          { "@type": "ListItem", position: 2, name: "Journal", item: `${site.url}/blog` },
          { "@type": "ListItem", position: 3, name: title, item: `${site.url}${path}` },
        ],
      },
    ],
  };
  return <>
    <SiteHeader />
    <main id="main-content" className="article-page">
      <script type="application/ld+json" dangerouslySetInnerHTML={{__html: JSON.stringify(graph).replace(/</g, "\\u003c")}} />
      <nav className="article-breadcrumb" aria-label="Breadcrumb">
        <Link href="/">Home</Link><span aria-hidden="true">/</span><Link href="/blog">Journal</Link><span aria-hidden="true">/</span><span>{category}</span>
      </nav>
      <article>
        <header className="article-heading">
          <span className="eyebrow">{category}</span>
          <h1>{title}</h1>
          <p className="article-deck">{description}</p>
          <div className="article-meta">
            <span>By Your Optimiser</span><time dateTime={published}>{new Date(`${published}T12:00:00Z`).toLocaleDateString("en-GB", {day:"numeric",month:"long",year:"numeric", timeZone:"America/Chicago"})}</time>
            <span>{minutes} min read</span>{updated && updated !== published && <span>Updated <time dateTime={updated}>{new Date(`${updated}T12:00:00Z`).toLocaleDateString("en-GB", {day:"numeric",month:"long",year:"numeric",timeZone:"America/Chicago"})}</time></span>}
          </div>
        </header>
        <figure className="article-cover">
          <Image src={image} alt={imageAlt} width={1440} height={960} sizes="(max-width: 760px) 88vw, 1100px" />
          <figcaption>Editorial illustration created for Your Optimiser.</figcaption>
        </figure>
        <div className="article-grid">
          <aside className="article-sidebar">
            <nav aria-label="In this article"><span className="eyebrow">IN THIS ARTICLE</span><ol>{contents.map(item => <li key={item.id}><a href={`#${item.id}`}>{item.title}</a></li>)}</ol></nav>
            <div className="article-sidebar-note"><strong>Your autonomous SEO agent.</strong><p>Checks, focused fixes and a clear record of what was verified.</p><Link href="/how-it-works">See how it works →</Link></div>
          </aside>
          <div className="article-prose">
            <aside className="article-takeaway"><span className="eyebrow">THE TAKEAWAY</span><p>{takeaway}</p></aside>
            {children}
            <div className="article-end"><span className="eyebrow">PUT IT INTO PRACTICE</span><h2>Give the next website update an extra pair of eyes.</h2><p>Your Optimiser is an autonomous SEO agent. It investigates relevant changes, proposes tested repairs and checks the deployed result. Your team reviews hosted pull requests.</p><Link href="/login?mode=register" prefetch={false} className="button">Meet your SEO agent ↗</Link><Link href="/blog" className="text-link">More from the journal →</Link></div>
          </div>
        </div>
      </article>
    </main>
    <SiteFooter />
  </>;
}
