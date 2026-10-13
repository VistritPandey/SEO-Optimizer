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
          <a href="#how">See it work</a>
          <a href="#pricing">Pricing</a>
          <Link href="/login">Sign in ↗</Link>
        </nav>
      </header>
      <main>
        <section className="hero">
          <div>
            <span className="eyebrow">YOUR AI AGENT FOR ONGOING SEO</span>
            <h1>
              Your website evolves.
              <br />
              <em>Your SEO needs to keep up.</em>
            </h1>
            <p>
              A new page. A fresh design. A product update. Your Optimiser
              checks what changed, fixes confirmed search problems and checks
              the result—so you can keep moving.
            </p>
            <div className="actions">
              <a className="button" href="#how">
                Try the interactive demo ↓
              </a>
              <Link className="text-link" href="/login?mode=register">
                Get started free ↗
              </Link>
            </div>
            <small>
              For the people building a business, not just the people writing
              its code.
            </small>
          </div>
          <div className="hero-outcome">
            <div className="hero-outcome-heading">
              <span className="eyebrow">A WEBSITE UPDATE · EXAMPLE</span>
              <span className="pill">
                <span className="dot" />
                Being looked after
              </span>
            </div>
            <h3>
              You changed the homepage.
              <br />
              We checked the next step.
            </h3>
            <p>
              The page looked great. Its main shopping button led nowhere. Your
              Optimiser caught the problem and prepared the fix.
            </p>
            <div className="hero-activity">
              <span>↗</span>
              <div>
                <strong>Collection link repaired</strong>
                <small>Visitors can reach the products again.</small>
              </div>
            </div>
            <div className="hero-activity">
              <span>≡</span>
              <div>
                <strong>Page description restored</strong>
                <small>Based on the page’s existing content.</small>
              </div>
            </div>
            <div className="hero-activity">
              <span>✓</span>
              <div>
                <strong>Website checked after the fix</strong>
                <small>Then back to watching for the next update.</small>
              </div>
            </div>
            <a className="text-link" href="#how">
              Walk through the whole story →
            </a>
          </div>
        </section>
        <section className="promise" aria-label="The ongoing process">
          <span>NOTICE THE CHANGE</span>
          <span>CHECK WHAT MATTERS</span>
          <span>FIX WHAT’S CONFIRMED</span>
          <span>KEEP WATCHING</span>
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
          <details className="customer-video">
            <summary>▷ Prefer to watch? See the customer walkthrough</summary>
            <video
              controls
              playsInline
              preload="none"
              poster="/demo-poster.png"
              aria-label="Your Optimiser customer walkthrough"
            >
              <source src="/demo.mp4" type="video/mp4" />
              <track
                kind="captions"
                src="/demo-captions.vtt"
                srcLang="en"
                label="English"
                default
              />
              Your browser does not support video playback.
            </video>
            <p>
              <small>
                An illustrated customer journey based on a recorded website
                repair. It shows the workflow, not a promise of higher rankings.
              </small>
            </p>
          </details>
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
            <h2>Free to get started.</h2>
            <p>
              Connect your website once. Follow its checks and improvements from
              one workspace. Start with the free plan; paid plans will come
              later.
            </p>
          </div>
          <article className="price-card">
            <span className="pill">FREE PLAN</span>
            <h3>Your first workspace</h3>
            <strong>
              $0 <small>/ month</small>
            </strong>
            <ul>
              <li>Up to 3 connected websites</li>
              <li>100 checks and follow-up tasks per month</li>
              <li>Findings, proposed fixes and activity history</li>
              <li>Choose the websites the agent can access</li>
            </ul>
            <Link className="button" href="/login?mode=register">
              Get started free ↗
            </Link>
            <p>No payment required.</p>
          </article>
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
            finding to a tested change—and keeps watching afterward.
          </p>
          <Link className="button" href="/login?mode=register">
            Give your website a working partner ↗
          </Link>
        </section>
      </main>
      <footer className="marketing-footer">
        <span>Your Optimiser</span>
        <span>Ongoing SEO care. Clear changes. Checked results.</span>
        <Link href="/login">Your workspace ↗</Link>
      </footer>
    </>
  );
}
