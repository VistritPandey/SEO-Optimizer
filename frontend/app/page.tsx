import Link from "next/link";
import { Workflow } from "@/components/Workflow";
export default function Home() {
  return (
    <>
      <header className="marketing-nav">
        <Link className="brand" href="/">
          y<span>Your Optimiser</span>
        </Link>
        <nav aria-label="Main">
          <a href="#how">How it works</a>
          <a href="#pricing">Pricing</a>
          <Link href="/login">Sign in ↗</Link>
        </nav>
      </header>
      <main>
        <section className="hero">
          <div>
            <span className="eyebrow">A LITTLE LESS GUESSWORK</span>
            <h1>
              A better website.
              <br />
              <em>A clearer way there.</em>
            </h1>
            <p>
              Your website deserves more than a list of things to fix. Give it a
              working partner that finds search problems, makes supported
              changes, and checks what actually improved.
            </p>
            <div className="actions">
              <Link className="button" href="/login?mode=register">
                Start your free workspace ↗
              </Link>
              <a className="text-link" href="#how">
                See the process ↓
              </a>
            </div>
            <small>
              SEO foundations. AI discovery. Your repository, your decisions.
            </small>
          </div>
          <div className="hero-sheet">
            <span className="eyebrow">
              WHAT AN IMPROVEMENT LOOKS LIKE · EXAMPLE
            </span>
            <div className="sheet-row">
              <span>Product page</span>
              <span className="pill">Evidence collected</span>
            </div>
            <h3>A product worth finding.</h3>
            <div className="example-code">
              <span className="removed">Canonical → preview.example.test</span>
              <span className="added">
                Canonical → www.example.test/product
              </span>
            </div>
            <ol className="receipt">
              <li>Confirm the public page and source</li>
              <li>Preserve pricing, availability and private previews</li>
              <li>Open a PR with the verified change</li>
              <li>Check the deployed page after merge</li>
            </ol>
            <div className="sheet-foot">
              <span className="dot" />A record of the change and its evidence
            </div>
          </div>
        </section>
        <section className="promise">
          <span>SEARCH FOUNDATIONS</span>
          <span>USEFUL, SUPPORTED CONTENT</span>
          <span>AI ANSWER VISIBILITY</span>
          <span>VERIFIED CHANGES</span>
        </section>
        <section className="section marketing-section" id="how">
          <span className="eyebrow">ONE CONTINUOUS PROCESS</span>
          <h2>
            From a finding
            <br />
            <em>to a verified improvement.</em>
          </h2>
          <Workflow />
        </section>
        <section className="feature-grid marketing-section">
          <article>
            <span className="number">01</span>
            <h3>Fix what gets in the way.</h3>
            <p>
              Crawling, indexing, canonicals, structured data, internal links
              and page experience. Evidence determines whether a change is
              needed.
            </p>
          </article>
          <article>
            <span className="number">02</span>
            <h3>Make the content worth finding.</h3>
            <p>
              Turn your verified business facts and original material into
              useful refreshes. Missing information stays a dependency until you
              supply it.
            </p>
          </article>
          <article>
            <span className="number">03</span>
            <h3>Learn without pretending.</h3>
            <p>
              Measure citations separately from rankings and traffic. Run
              repeatable experiments; distinguish observations from proven
              outcomes.
            </p>
          </article>
        </section>
        <section className="section marketing-section pricing" id="pricing">
          <div>
            <span className="eyebrow">START SMALL. BUILD SOMETHING GOOD.</span>
            <h2>Free to get started.</h2>
            <p>
              Hosted workspaces use managed AI. Run the open-source Python
              worker locally with your own Ollama model or paid API account.
            </p>
          </div>
          <article className="price-card">
            <span className="pill">AVAILABLE AT LAUNCH</span>
            <h3>Free workspace</h3>
            <strong>
              $0 <small>/ month</small>
            </strong>
            <ul>
              <li>Up to 3 connected projects</li>
              <li>100 runs per month, including follow-ups and probes</li>
              <li>Evidence, findings and PR activity</li>
              <li>Repository-scoped GitHub App access</li>
            </ul>
            <Link className="button" href="/login?mode=register">
              Create workspace ↗
            </Link>
            <p>Paid plans will come later. No payment required today.</p>
          </article>
        </section>
        <section className="closing marketing-section">
          <h2>
            Your code.
            <br />
            <em>A working partner.</em>
          </h2>
          <p>
            Incremental audits focus on affected website routes. Unchanged
            inputs can reuse model results, while periodic audits catch changes
            outside the repository.
          </p>
          <Link className="button" href="/login?mode=register">
            Let’s get your website ready ↗
          </Link>
        </section>
      </main>
      <footer className="marketing-footer">
        <span>Your Optimiser</span>
        <span>Measured improvements. Evidence before action.</span>
        <Link href="/login">Your workspace ↗</Link>
      </footer>
    </>
  );
}
