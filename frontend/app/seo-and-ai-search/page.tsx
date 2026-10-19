import Link from "next/link";
import { EditorialPage } from "@/components/EditorialPage";
import { pageMetadata } from "@/lib/site";

export const metadata = pageMetadata(
  "Ongoing SEO and AI search optimisation",
  "Understand what Your Optimiser checks: technical SEO, useful page content, consistent business facts and foundations for search and AI discovery.",
  "/seo-and-ai-search",
);

export default function Page() {
  return (
    <EditorialPage
      eyebrow="BE EASY TO FIND. BE CLEAR WHEN YOU ARE."
      title={
        <>
          The foundations matter.
          <br />
          <em>Every time you ship.</em>
        </>
      }
      intro="Search engines and AI answers need clear, accessible information. Your Optimiser looks after the details that can quietly drift as your website grows."
    >
      <section>
        <h2>Make the right pages discoverable.</h2>
        <p>
          A page can look finished and still send the wrong signals. We check
          crawl and indexing directives, response codes, redirects, canonical
          URLs, sitemaps and internal links. Intentional preview pages and
          private areas should stay private.
        </p>
        <p>
          <strong>A practical example:</strong> a redesigned landing page keeps
          a canonical URL pointing at a retired page. That conflict needs
          evidence and a focused correction, not a rewrite of the whole site.
        </p>
      </section>
      <section>
        <h2>Say what your business actually offers.</h2>
        <p>
          Titles, descriptions, headings and structured data should agree with
          the visible page. Product prices, availability, service areas and
          opening hours should come from trusted facts. When those facts are
          missing, the agent records the dependency.
        </p>
        <p>
          Useful content starts with what you know: original explanations, real
          product details and evidence you can support. We do not invent
          reviews, customer results or product benefits.
        </p>
      </section>
      <section>
        <h2>Give AI search something reliable to work with.</h2>
        <p>
          GEO, AEO and LLM visibility describe related work across different
          answer engines. The useful foundation is understandable content,
          consistent entities, accessible pages and accurate sources. No
          universal “AI visibility score” can prove that every engine
          understands you.
        </p>
        <p>
          We separate crawler access, training preferences and user-directed
          retrieval. We also keep citation observations separate from rankings,
          website visits and conversions.
        </p>
        <p>
          Google’s own guidance says existing SEO foundations still apply to its
          AI search features. It does not use <code>llms.txt</code> as a ranking
          mechanism. We publish ours as a helpful product index for readers and
          tools that choose to use it.
        </p>
        <a
          className="text-link"
          href="https://developers.google.com/search/docs/fundamentals/ai-optimization-guide"
          target="_blank"
          rel="noopener noreferrer"
        >
          Read Google’s AI search guidance ↗
        </a>
      </section>
      <section>
        <h2>Check the experience, not just the markup.</h2>
        <p>
          Rendering, images, navigation and layout can all affect whether a page
          works for visitors. Screenshots can help answer visual questions, but
          do not establish indexing status or real-world Core Web Vitals. Lab
          observations and field measurements need their own evidence.
        </p>
      </section>
      <section>
        <h2>Match the website you actually run.</h2>
        <p>
          An online shop needs product variants, stock, prices and useful
          category navigation. A service business needs verified location and
          service information. An international website needs coherent language
          targeting, localisation and reciprocal hreflang.
        </p>
        <p>
          The agent applies relevant checks to your project context. It should
          not add local-business details to a software product or turn a
          deliberate private page into a public one.
        </p>
      </section>
      <aside className="editorial-note">
        <strong>A better process, not a ranking promise.</strong>
        <p>
          Confirmed fixes can be verified. Search rankings, indexing, AI
          citations and business results depend on systems and conditions
          outside this product. Measure those outcomes separately.
        </p>
      </aside>
      <Link className="button" href="/how-it-works">
        See the workflow →
      </Link>
    </EditorialPage>
  );
}
