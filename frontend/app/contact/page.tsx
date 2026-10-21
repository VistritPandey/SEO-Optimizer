import Link from "next/link";
import { EditorialPage } from "@/components/EditorialPage";
import { ContactForm } from "@/components/ContactForm";
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
      intro="A product question, a problem to solve or an idea to share. Send a message to the people building Your Optimiser."
    >
      <section>
        <h2>Let’s talk.</h2>
        <p>
          Tell us what you expected and what happened, along with the page or
          feature involved. For account or security questions, start with a
          brief description so we can arrange a suitable follow-up.
        </p>
        <ContactForm />
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
