import Link from "next/link";
import { EditorialPage } from "@/components/EditorialPage";
import { Reveal } from "@/components/Reveal";
import { Workflow } from "@/components/Workflow";
import { pageMetadata } from "@/lib/site";

export const metadata = pageMetadata(
  "How Your Optimiser works",
  "From a website change to a reviewed, tested fix. See how Your Optimiser connects GitHub, checks the right pages and verifies the deployed result.",
  "/how-it-works",
);

const steps = [
  [
    "01",
    "Connect the website you care about.",
    "Create a workspace, install the GitHub App on the repository you choose, and add your deployed website. Tell the agent which branch and folders matter, what your business does and which pages are intentionally private.",
  ],
  [
    "02",
    "Let your team keep building.",
    "A change on the monitored branch starts a check. The agent focuses on the affected pages and shared dependencies. Periodic checks help catch changes that happen between repository events.",
  ],
  [
    "03",
    "Make the problem prove itself.",
    "The agent checks source files and the served website. A broken link needs a broken destination. A product claim needs a trusted fact. Missing evidence becomes a question to resolve, rather than an invented answer.",
  ],
  [
    "04",
    "Review a small, useful fix.",
    "When the evidence supports a change, the agent edits the permitted files, runs the configured checks and opens a GitHub pull request. You can see the reason, the change and the checks before your team merges it.",
  ],
  [
    "05",
    "Check what actually went live.",
    "A merged pull request is a step, not the result. The agent waits for the configured deployment and checks the served page again. Your workspace keeps a record of the finding and what was verified.",
  ],
];

export default function Page() {
  return (
    <EditorialPage
      wide
      eyebrow="A WORKING AGENT, FROM START TO FINISH"
      title={
        <>
          You make the next move.
          <br />
          <em>We check what follows.</em>
        </>
      }
      intro="Your website will keep changing. Give its search foundations a process that keeps up, without turning every update into another manual audit."
    >
      <div className="process-list">
        {steps.map(([number, title, body]) => (
          <Reveal key={number}>
            <article>
              <span className="process-number">{number}</span>
              <div>
                <h2>{title}</h2>
                <p>{body}</p>
              </div>
            </article>
          </Reveal>
        ))}
      </div>
      <section className="editorial-demo" aria-labelledby="demo-title">
        <span className="eyebrow">TAKE IT FOR A SPIN</span>
        <h2 id="demo-title">One update. Two possible outcomes.</h2>
        <p>
          Try a broken update, then a healthy one. See the difference between a
          justified fix and a page that should stay exactly as it is.
        </p>
        <Workflow />
      </section>
      <section className="editorial-split">
        <div>
          <span className="eyebrow">YOUR TEAM KEEPS THE FINAL SAY</span>
          <h2>Review is part of the workflow.</h2>
        </div>
        <div>
          <p>
            Hosted changes arrive as pull requests. Your team reviews and merges
            them. Comments on a tracked agent pull request can trigger a
            follow-up check from an authorised repository collaborator.
          </p>
          <p>
            The agent respects configured paths, private pages and crawler
            preferences. It does not replace missing business facts with
            plausible-sounding copy.
          </p>
          <Link href="/security" className="text-link">
            Read about access and control →
          </Link>
        </div>
      </section>
      <div className="editorial-cta">
        <h2>Your next update can have backup.</h2>
        <Link className="button" href="/login?mode=register">
          Create your free workspace ↗
        </Link>
        <small>
          GitHub integration · reviewable changes · no payment required
        </small>
      </div>
    </EditorialPage>
  );
}
