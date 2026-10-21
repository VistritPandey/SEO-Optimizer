import Link from "next/link";
import Image from "next/image";
import { ArticleCards } from "@/components/ArticleCards";
import { Workflow } from "@/components/Workflow";
import { HeroWorkflow } from "@/components/HeroWorkflow";
import { WalkthroughVideo } from "@/components/WalkthroughVideo";
import { SiteHeader, SiteFooter } from "@/components/SiteChrome";
import { Reveal } from "@/components/Reveal";
import { site } from "@/lib/site";

export const metadata = { alternates: { canonical: "/" } };

const questions = [
  [
    "What happens after I connect my website?",
    "Connect a GitHub repository and your deployed website, choose the branch and pages that matter, and add trusted business facts. The agent starts an audit and checks relevant website changes afterward.",
  ],
  [
    "Does it change my website without asking?",
    "Hosted fixes are proposed as GitHub pull requests. Your team reviews and merges them. The agent then checks the configured deployment and served page to verify the result.",
  ],
  [
    "What if my update hasn’t broken anything?",
    "The agent records what was checked and leaves healthy pages alone. A useful check does not need to create an edit.",
  ],
  [
    "Will this improve rankings or get me cited by AI?",
    "The product helps address supported technical and content problems. Search indexing, rankings, AI citations and traffic are separate outcomes that no tool can guarantee. We keep those measurements separate from verified fixes.",
  ],
  [
    "What is free, and what comes next?",
    "The open-source version is free to run with your own setup. Hosted early access currently includes up to three connected websites and 100 audit and follow-up jobs per month. Paid hosted plans may follow; using the current free service does not sign you up for a charge.",
  ],
  [
    "Which website platforms can I connect?",
    "The hosted integration is GitHub. Your website’s source must be in a repository you can authorise, with a deployed URL the agent can inspect. We do not currently offer direct CMS or other source-control integrations.",
  ],
];

const structuredData = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "@id": `${site.url}/#organization`,
      name: site.name,
      alternateName: "YourOptimiser",
      url: site.url,
      logo: {
        "@type": "ImageObject",
        url: `${site.url}/brand/logo.png`,
        width: 512,
        height: 512,
      },
    },
    {
      "@type": "WebSite",
      "@id": `${site.url}/#website`,
      name: site.name,
      alternateName: "YourOptimiser",
      url: site.url,
      publisher: { "@id": `${site.url}/#organization` },
      inLanguage: "en",
    },
    {
      "@type": "SoftwareApplication",
      "@id": `${site.url}/#application`,
      name: site.name,
      url: site.url,
      applicationCategory: "BusinessApplication",
      operatingSystem: "Web",
      description: site.description,
      publisher: { "@id": `${site.url}/#organization` },
      offers: {
        "@type": "Offer",
        price: "0",
        priceCurrency: "USD",
        url: `${site.url}/#pricing`,
        description:
          "Free plan: up to 3 websites and 100 audit/follow-up jobs per month.",
      },
    },
  ],
};

export default function Home() {
  return (
    <>
      <SiteHeader />
      <main id="main-content">
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify(structuredData).replace(/</g, "\\u003c"),
          }}
        />
        <section className="hero">
          <div>
            <span className="eyebrow">
              CONTINUOUS CARE. EVIDENCE BEFORE ACTION.
            </span>
            <h1>
              Your autonomous
              <br />
              <em>SEO agent.</em>
            </h1>
            <p>
              Your website keeps changing. Your Optimiser watches the updates,
              finds supported SEO issues, prepares tested fixes in GitHub and
              checks the result after deployment.
            </p>
            <div className="actions">
              <a className="button" href="#how">
                Try the interactive demo ↓
              </a>
              <Link
                className="text-link"
                href="/login?mode=register"
                prefetch={false}
              >
                Get started free ↗
              </Link>
            </div>
            <small>
              Connect GitHub once. Review useful fixes. Keep your team moving.
            </small>
          </div>
          <HeroWorkflow />
        </section>
        <section className="promise" aria-label="The ongoing process">
          <span>NOTICE THE CHANGE</span>
          <span>CHECK WHAT MATTERS</span>
          <span>FIX WHAT’S CONFIRMED</span>
          <span>KEEP WATCHING</span>
        </section>
        <section
          className="care-story marketing-section"
          aria-labelledby="care-title"
        >
          <div>
            <span className="eyebrow">
              THE WORK THAT SLIPS BETWEEN THE BIG UPDATES
            </span>
            <h2 id="care-title">
              The page looks right.
              <br />
              <em>But does everything still work?</em>
            </h2>
          </div>
          <div>
            <p>
              A shopping link points to a page that moved. A new template drops
              a description. A product’s search information stops matching its
              price. Small details can drift long before the next audit.
            </p>
            <p>
              Your Optimiser gives those details a follow-through: current
              evidence, a focused change, your team’s review, then a check of
              what went live.
            </p>
            <Link href="/how-it-works" className="text-link">
              From website update to verified fix →
            </Link>
          </div>
        </section>
        <section className="section marketing-section" id="how">
          <div className="customer-intro">
            <div>
              <span className="eyebrow">
                TRY IT. YOU’RE IN THE DRIVER’S SEAT.
              </span>
              <h2>
                A website update.
                <br />
                <em>See what happens next.</em>
              </h2>
            </div>
            <p>
              Publish an example update, explore the problem, review the fix and
              try the button afterward. Or choose a healthy update and see why
              the agent leaves it alone.
            </p>
          </div>
          <Workflow />
          <WalkthroughVideo />
        </section>
        <section
          className="coverage marketing-section"
          aria-labelledby="coverage-title"
        >
          <div className="customer-intro">
            <div>
              <span className="eyebrow">
                A LITTLE CARE, IN THE RIGHT PLACES
              </span>
              <h2 id="coverage-title">
                Your whole offer.
                <br />
                <em>A clearer path to it.</em>
              </h2>
            </div>
            <p>
              Checks match your website and the evidence available. Missing
              facts stay visible; working pages keep their place.
            </p>
          </div>
          <div className="coverage-rows">
            {[
              [
                "01",
                "The way in",
                "Crawling, indexing signals, redirects, canonical URLs and internal links.",
                "Help the right pages stay accessible.",
              ],
              [
                "02",
                "The story you tell",
                "Page titles, descriptions, useful headings and content grounded in your actual offer.",
                "Keep your message clear and consistent.",
              ],
              [
                "03",
                "The facts that matter",
                "Product details, business information, structured data and language targeting.",
                "Make the information agree.",
              ],
              [
                "04",
                "The next answer",
                "Discovery settings, clear entities, supported claims and separate citation observations.",
                "Build reliable foundations for AI search.",
              ],
            ].map(([number, title, body, outcome]) => (
              <Reveal key={number}>
                <article>
                  <span>{number}</span>
                  <h3>{title}</h3>
                  <p>{body}</p>
                  <small>{outcome}</small>
                </article>
              </Reveal>
            ))}
          </div>
          <Link href="/seo-and-ai-search" className="text-link">
            Explore what we look after →
          </Link>
        </section>
        <section className="review-story marketing-section">
          <div>
            <span className="eyebrow">LESS GUESSWORK. A BETTER HANDOVER.</span>
            <h2>
              “What changed?”
              <br />
              <em>There’s a record for that.</em>
            </h2>
            <p>
              See the finding, the evidence, the proposed fix and the check
              afterward. Keep ownership of the website without chasing every
              detail yourself.
            </p>
            <Link href="/security" className="text-link">
              Your access. Your review. Your control. →
            </Link>
          </div>
          <div
            className="review-receipt"
            aria-label="Illustrative repair record"
          >
            <span className="eyebrow">
              EXAMPLE REPAIR RECORD · FICTIONAL STORE
            </span>
            <h3>A clear path to the collection.</h3>
            <dl>
              <div>
                <dt>Observed</dt>
                <dd>Homepage button opens a missing page</dd>
              </div>
              <div>
                <dt>Proposed</dt>
                <dd>Restore the existing collection link</dd>
              </div>
              <div>
                <dt>Reviewed</dt>
                <dd>Your team approves the pull request</dd>
              </div>
              <div>
                <dt>Verified</dt>
                <dd>The deployed button reaches the collection</dd>
              </div>
            </dl>
            <div className="receipt-end">
              <span className="dot" /> Back to watching the website
            </div>
          </div>
        </section>
        <section
          className="feature-grid marketing-section"
          aria-label="What Your Optimiser looks after"
        >
          <article>
            <span className="number">01 / GET FOUND</span>
            <h3>Keep the path to your business clear.</h3>
            <p>
              Catch broken links, missing page information and conflicting
              signals that make a website harder to understand. Confirm the
              problem, then make a focused fix.
            </p>
          </article>
          <article>
            <span className="number">02 / BE UNDERSTOOD</span>
            <h3>Help search and AI understand your offer.</h3>
            <p>
              Keep your pages, product details and business information clear
              and consistent. Build useful content from facts and original
              material you can stand behind.
            </p>
          </article>
          <article>
            <span className="number">03 / STAY IN CONTROL</span>
            <h3>A working agent. A clear record.</h3>
            <p>
              See what needs attention, what changed and what was checked
              afterward. Choose which changes need review. Healthy pages stay
              alone; missing facts come back to you.
            </p>
          </article>
        </section>
        <section className="section marketing-section pricing" id="pricing">
          <div>
            <span className="eyebrow">GIVE YOUR WEBSITE A LITTLE BACKUP</span>
            <h2>Start free. Keep your options open.</h2>
            <p>
              Connect your website once. Follow its checks and improvements from
              one workspace. Hosted early access is free; paid hosted plans will
              follow as the service grows.
            </p>
            <a
              className="text-link"
              href={site.repository}
              target="_blank"
              rel="noopener noreferrer"
            >
              Prefer your own setup? The open-source version is free ↗
            </a>
          </div>
          <article className="price-card">
            <span className="pill">FREE PLAN</span>
            <h3>Your first workspace</h3>
            <strong>
              $0 <small>/ month</small>
            </strong>
            <ul>
              <li>Up to 3 connected websites</li>
              <li>100 audits and follow-up tasks per month</li>
              <li>Findings, proposed fixes and activity history</li>
              <li>Choose the websites the agent can access</li>
            </ul>
            <Link
              className="button"
              href="/login?mode=register"
              prefetch={false}
            >
              Get started free ↗
            </Link>
            <p>No payment required.</p>
          </article>
        </section>
        <section
          className="faq-section marketing-section"
          aria-labelledby="faq-title"
        >
          <div>
            <span className="eyebrow">BEFORE YOU HAND OVER THE BUSYWORK</span>
            <h2 id="faq-title">
              Good questions.
              <br />
              <em>Straight answers.</em>
            </h2>
            <Link href="/contact" className="text-link">
              Something else on your mind? →
            </Link>
          </div>
          <div className="faq-list">
            {questions.map(([question, answer]) => (
              <details key={question}>
                <summary>{question}</summary>
                <p>{answer}</p>
              </details>
            ))}
          </div>
        </section>
        <section
          className="journal-home marketing-section"
          aria-labelledby="journal-title"
        >
          <div className="journal-section-heading">
            <div>
              <span className="eyebrow">THE BLOG</span>
              <h2 id="journal-title">
                Good SEO starts with
                <br />
                <em>understanding the work.</em>
              </h2>
            </div>
            <Link href="/blog" className="text-link">
              Explore the blog →
            </Link>
          </div>
          <ArticleCards />
        </section>
        <section
          className="journal-guide marketing-section"
          aria-labelledby="guide-title"
        >
          <Image
            src="/editorial/clear-discovery.webp"
            alt="Layered ivory paper revealing a clear green path."
            width={1440}
            height={960}
            sizes="(max-width: 760px) 88vw, 40vw"
          />
          <div>
            <span className="eyebrow">A PRACTICAL GUIDE FOR YOUR TEAM</span>
            <h2 id="guide-title">
              An SEO habit that survives the next launch.
            </h2>
            <p>
              Follow a website change, establish the evidence, review a fix and
              measure what happened. A useful process whether you use an agent
              or do the work yourself.
            </p>
            <Link href="/guides/continuous-seo" className="text-link">
              Read the ongoing SEO guide →
            </Link>
          </div>
        </section>
        <section className="closing marketing-section">
          <span className="eyebrow">THE WORK CONTINUES AFTER THE AUDIT</span>
          <h2>
            Keep building your business.
            <br />
            <em>Keep your website looked after.</em>
          </h2>
          <p>
            Updates trigger checks of the affected pages. Regular checks catch
            problems in between. The agent follows through from a confirmed
            finding to a tested change, and keeps watching afterward.
          </p>
          <Link className="button" href="/login?mode=register" prefetch={false}>
            Give your website a working partner ↗
          </Link>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
