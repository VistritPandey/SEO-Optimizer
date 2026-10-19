import Link from "next/link";
import { EditorialPage } from "@/components/EditorialPage";
import { pageMetadata, site } from "@/lib/site";

export const metadata = pageMetadata(
  "Contact Your Optimiser",
  "Get help with Your Optimiser or request a private channel for account, privacy and security questions.",
  "/contact",
);

const privateRequest = `${site.repository}/issues/new?title=Private%20contact%20request&body=Please%20provide%20a%20private%20contact%20channel%20for%20an%20account%2C%20privacy%20or%20security%20request.%20No%20sensitive%20information%20is%20included%20here.`;

export default function Page() {
  return (
    <EditorialPage
      eyebrow="LET’S GET YOU TO THE RIGHT PLACE"
      title={
        <>
          A question?
          <br />
          <em>We’re listening.</em>
        </>
      }
      intro="Your Optimiser is in its early public release. Support is currently handled manually by the project maintainers through GitHub."
    >
      <section>
        <h2>Product questions and reproducible problems.</h2>
        <p>
          Tell us what you expected and what happened. A public issue is useful
          for a general question or a bug that can be described without sharing
          customer data. Remove private repository URLs, tokens, screenshots
          with personal details and account identifiers.
        </p>
        <a
          className="button"
          href={`${site.repository}/issues`}
          target="_blank"
          rel="noopener noreferrer"
        >
          Open the support tracker ↗
        </a>
      </section>
      <section>
        <h2>Privacy, account or security requests.</h2>
        <p>
          Start with a request for a private contact channel. The button below
          opens a prefilled GitHub issue containing only that request. You
          choose whether to submit it. Wait for a private channel before sharing
          your email address, account details, private code or the details of a
          vulnerability.
        </p>
        <a
          className="button secondary"
          href={privateRequest}
          target="_blank"
          rel="noopener noreferrer"
        >
          Request a private contact channel ↗
        </a>
        <p className="contact-note">
          This initial request is public on GitHub. Do not add sensitive
          information. Identity verification may be needed before account data
          can be released or removed.
        </p>
      </section>
      <section>
        <h2>Want to stop repository access now?</h2>
        <p>
          Disconnect GitHub in your workspace and remove the App installation
          from your GitHub account or organisation settings. This stops future
          access without waiting for a support response.
        </p>
        <Link href="/dashboard" className="text-link">
          Open your workspace →
        </Link>
      </section>
    </EditorialPage>
  );
}
