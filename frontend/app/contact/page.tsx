import Link from "next/link";
import { EditorialPage } from "@/components/EditorialPage";
import { pageMetadata, site } from "@/lib/site";

export const metadata = pageMetadata(
  "Contact Your Optimiser",
  "Get help with Your Optimiser or request a private channel for account, privacy and security questions.",
  "/contact",
);

const support = `mailto:${site.supportEmail}`;

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
      intro="Your Optimiser is in its early public release. Support is handled by the project maintainers. Use our support address for product, account, privacy and security questions."
    >
      <section>
        <h2>Product questions and reproducible problems.</h2>
        <p>
          Tell us what you expected and what happened, along with the page or
          feature involved. Remove tokens, passwords and unnecessary customer
          data from screenshots or attachments.
        </p>
        <a
          className="button"
          href={support}
          target="_blank"
          rel="noopener noreferrer"
        >
          Email support ↗
        </a>
      </section>
      <section>
        <h2>Privacy, account or security requests.</h2>
        <p>
          Email us privately. Include enough context to describe your request,
          but never send passwords, access tokens or private signing keys. For a
          vulnerability, begin with a brief description and ask how to share
          sensitive reproduction details securely.
        </p>
        <a
          className="button secondary"
          href={`${support}?subject=Private%20support%20request`}
          target="_blank"
          rel="noopener noreferrer"
        >
          Contact us privately ↗
        </a>
        <p className="contact-note">
          Identity verification may be needed before account data can be
          released or removed. Requests are handled manually.
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
