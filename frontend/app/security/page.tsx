import Link from "next/link";
import { EditorialPage } from "@/components/EditorialPage";
import { pageMetadata } from "@/lib/site";

export const metadata = pageMetadata(
  "Security and control",
  "Understand GitHub App access, pull request reviews, protected credentials and the evidence boundaries behind Your Optimiser’s SEO agent.",
  "/security",
);

export default function Page() {
  return (
    <EditorialPage
      eyebrow="CLEAR BOUNDARIES. USEFUL AUTONOMY."
      title={
        <>
          Your website.
          <br />
          <em>Your final say.</em>
        </>
      }
      intro="An agent that can change code needs more than a good prompt. Here is how the hosted product limits access, prepares changes and keeps the record visible."
    >
      <section>
        <h2>You choose the repositories.</h2>
        <p>
          Install the service’s GitHub App on the repositories you select. Your
          Optimiser uses the App’s installation access to read code and prepare
          pull requests. It does not ask each customer to hand over a personal
          GitHub token.
        </p>
        <p>
          You can disconnect GitHub from your workspace or revoke the
          installation in GitHub. Disconnection pauses affected projects.
          Revoking access does not undo changes you previously merged.
        </p>
      </section>
      <section>
        <h2>Changes arrive for review.</h2>
        <p>
          The hosted agent proposes code changes in GitHub pull requests. Your
          team reviews and merges them. Follow-up comments are limited to
          tracked agent pull requests and authorised repository collaborators.
        </p>
        <p>
          Project configuration controls permitted paths and actions.
          Instructions encountered inside a page or source file are treated as
          untrusted content; they do not grant new permissions.
        </p>
      </section>
      <section>
        <h2>Credentials stay on the server.</h2>
        <p>
          Service credentials use Google Secret Manager. Stored application
          credentials and authorisation grants are encrypted by the backend.
          Browser Firebase settings identify the authentication project and are
          not administrator credentials.
        </p>
        <p>
          The API verifies account identity and tenant ownership before
          returning workspace records. Repository checks use a separate
          execution identity without the application’s database or secret
          permissions.
        </p>
      </section>
      <section>
        <h2>Evidence has limits.</h2>
        <p>
          The agent checks source files, website responses and relevant rendered
          content. Visual evidence can help diagnose a layout issue; it cannot
          establish indexing, ranking impact or real-world performance on its
          own.
        </p>
        <p>
          Private pages, crawler preferences, verified business facts and
          existing product behaviour are constraints to preserve. Missing
          evidence should produce an unresolved dependency, not an invented fix.
        </p>
      </section>
      <section>
        <h2>Understand what is processed.</h2>
        <p>
          Relevant repository files, page content, project context and optional
          screenshots may be processed by a third-party AI provider to perform a
          task. Avoid connecting repositories containing secrets or data you do
          not have permission to process. The provider may change as the service
          evolves.
        </p>
        <Link className="text-link" href="/privacy">
          Read the privacy notice →
        </Link>
      </section>
      <aside className="editorial-note">
        <strong>Report a concern privately.</strong>
        <p>
          Do not include tokens, private code or personal data in a public
          issue. Use the contact page to request a private reporting channel
          first.
        </p>
        <Link href="/contact" className="text-link">
          Contact the maintainers →
        </Link>
      </aside>
    </EditorialPage>
  );
}
