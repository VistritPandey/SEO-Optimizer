import Link from "next/link";
import { ArticleLayout } from "@/components/ArticleLayout";
import { pageMetadata } from "@/lib/site";

export const metadata = pageMetadata(
  "A practical guide to continuous SEO",
  "A website change is the start of an SEO check. Learn a practical process for detecting regressions, reviewing focused fixes and verifying what went live.",
  "/guides/continuous-seo",
);

export default function Page() {
  return (
    <ArticleLayout
      title="A practical guide to continuous SEO"
      description="A process for teams whose websites keep moving: follow the change, establish evidence, review a focused fix and verify what went live."
      category="THE FIELD GUIDE"
      path="/guides/continuous-seo"
      published="2026-10-19"
      updated="2026-10-20"
      minutes={5}
      image="/editorial/continuous-care.webp"
      imageAlt="A continuous green paper loop through three ivory frames."
      takeaway="Continuous SEO is a repeatable process. An autonomous SEO agent can carry the work from a relevant website change to a tested proposal and post-deployment verification."
      contents={[
        {id:"baseline",title:"Set a baseline"},
        {id:"scope",title:"Follow the change"},
        {id:"evidence",title:"Establish evidence"},
        {id:"review",title:"Review a focused fix"},
        {id:"verify",title:"Verify the live page"},
        {id:"measure",title:"Measure the right outcome"},
      ]}
    >
      <section id="baseline">
        <h2>1. Set the rules before checking the pages.</h2>
        <p>
          Write down which website is production, which branch publishes it,
          which folders affect public pages and which areas are intentionally
          private. Add trusted facts such as your business name, actual products
          and service locations. Those choices make an audit relevant.
        </p>
        <p>
          Keep a baseline of important pages: response status, title,
          description, canonical, main links and appropriate structured data.
          Where field performance data is available, record its source and date
          separately from a local speed test.
        </p>
      </section>
      <section id="scope">
        <h2>2. Follow the change to the pages it can affect.</h2>
        <p>
          A landing-page update deserves a check. An unrelated internal backend
          change may not. Shared navigation, templates and routing can affect
          more than the file that changed, so include those dependencies.
          Periodic reconciliation is the safety net for changes an event-based
          check could miss.
        </p>
        <p>
          In our illustrated store example, the homepage design still looks
          right after an update. The relevant change is the collection button’s
          destination and the missing page description. That is a much smaller
          problem than “the website needs an SEO overhaul.”
        </p>
      </section>
      <section id="evidence">
        <h2>3. Make every finding answer “how do we know?”</h2>
        <p>
          Follow the link and inspect the response. Compare the source and
          rendered page. Check whether the canonical target is intentional.
          Compare product markup with the visible price and trusted product
          facts. Keep those observations with their source, environment and
          collection time.
        </p>
        <p>
          A screenshot can show that a menu overlaps the heading. It cannot show
          that Google has indexed a page. A missing opening-hours value is a
          request for a verified business fact, not permission to guess.
        </p>
      </section>
      <section id="review">
        <h2>4. Make the smallest change that solves the confirmed problem.</h2>
        <p>
          Restore a link to the existing collection. Write the missing
          description from supported page content. Keep the design and working
          product behaviour intact. Run the project’s configured checks and put
          the change in a reviewable pull request.
        </p>
        <p>
          A healthy change deserves the same care: record what was checked and
          leave the page alone. Creating an edit is not evidence that the audit
          was useful.
        </p>
      </section>
      <section id="verify">
        <h2>5. Go back to the website after deployment.</h2>
        <p>
          A green test, an approved pull request and a live repair are different
          milestones. Wait for the relevant deployment, then inspect the served
          page. Does the collection open? Is the description present? Did the
          change introduce another broken path?
        </p>
        <p>
          Keep unverified outcomes visible. “Waiting for deployment” is more
          honest and useful than calling a proposed change a verified fix.
        </p>
      </section>
      <section id="measure">
        <h2>6. Keep technical fixes and business outcomes separate.</h2>
        <p>
          A working link can be checked immediately. Search impressions, clicks,
          rankings, AI citations and conversions need their own observations
          over time. A change in any one of those does not prove the repair
          caused it.
        </p>
        <p>
          For an AI-answer experiment, record the engine, questions, dates and
          repeated observations. Check that citations point to the right page
          and represent your business accurately. Keep the control and the cases
          where the engine did not search.
        </p>
      </section>
      <aside className="editorial-note">
        <strong>Your weekly review, in five questions.</strong>
        <ol>
          <li>What changed on the website?</li>
          <li>Which problems have current evidence?</li>
          <li>What is waiting for facts or review?</li>
          <li>Which fixes are verified on the live site?</li>
          <li>What did search, visitors and enquiries actually do?</li>
        </ol>
      </aside>
      <section>
        <h2>Make it a habit your team can sustain.</h2>
        <p>
          The point of continuous SEO is to give every meaningful update a
          sensible check, keep the record clear and spend less time
          rediscovering preventable problems. Your Optimiser turns that process
          into an ongoing agent workflow.
        </p>
        <Link className="button" href="/how-it-works">
          See the process in action →
        </Link>
      </section>
    </ArticleLayout>
  );
}
