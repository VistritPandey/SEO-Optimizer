import Link from "next/link";
import { EditorialPage } from "@/components/EditorialPage";
import { pageMetadata } from "@/lib/site";

export const metadata = pageMetadata(
  "Terms of service",
  "Terms for the hosted Your Optimiser service, including repository permissions, AI-generated changes, free-plan limits and your review responsibilities.",
  "/terms",
);

export default function Page() {
  return (
    <EditorialPage
      eyebrow="TERMS OF SERVICE · EFFECTIVE 23 OCTOBER 2026"
      title={
        <>
          Useful work.
          <br />
          <em>Clear expectations.</em>
        </>
      }
      intro="These terms cover the hosted Your Optimiser service operated by the project maintainers at youroptimiser.com. By using the hosted service, you agree to these terms and acknowledge the privacy notice."
    >
      <section>
        <h2>Accounts and authority.</h2>
        <p>
          Use accurate account information, protect your sign-in credentials and
          connect only websites and repositories you are authorised to manage.
          If you act for an organisation, you must have authority to do so. The
          service is intended for adults using it for business or professional
          projects.
        </p>
      </section>
      <section>
        <h2>What you authorise.</h2>
        <p>
          Connecting a project authorises the service to process the project
          information and relevant repository and website content needed to
          perform configured audits, prepare changes and verify results.
          Installing the GitHub App grants the access described by GitHub’s
          installation screen. Other platform connections use the permissions
          granted by their account authorization or credentials.
        </p>
        <p>
          Enabling connector writes permits supported field changes within
          project policy. Automatic application is a separate option. Some
          platforms save drafts or staged changes; you remain responsible for
          their publication. Verification of a saved field does not establish
          that a website is deployed, indexed or ranking.
        </p>
        <p>
          Your team remains responsible for reviewing proposed changes,
          configuring tests and deployment settings, and deciding whether to
          merge a pull request. AI output can be incomplete or incorrect. A
          successful automated check does not establish that every possible
          regression has been excluded.
        </p>
      </section>
      <section>
        <h2>Your content and credentials.</h2>
        <p>
          You retain rights you hold in your code and content. You give the
          service permission to process them as needed to provide the
          functionality you request, including through infrastructure and AI
          providers. You must have the rights and permissions needed for that
          processing.
        </p>
        <p>
          Do not intentionally submit credentials or sensitive data that the
          task does not require. Do not use the service to access another
          person’s systems without permission, create deceptive claims or
          reviews, abuse crawlers, distribute harmful code or bypass project
          permissions and usage limits.
        </p>
      </section>
      <section>
        <h2>The free plan and future pricing.</h2>
        <p>
          The current free hosted plan supports up to three connected websites
          and 100 audit and follow-up jobs per month, shared across the
          workspace. Failed or repeated work can consume usage according to the
          recorded job quota. No payment details are required for the current
          free plan.
        </p>
        <p>
          Features, limits and pricing may change. A future paid plan will
          require separate pricing information and affirmative purchase
          acceptance. Using the current free service does not authorise an
          automatic charge.
        </p>
        <p>
          Optional keyword-data and AI-answer experiments can consume paid
          third-party API usage using the credentials you connect. These
          experiments run on explicit collection, not periodic monitoring.
          Review the provider’s pricing and your own account limits; a missing
          returned cost does not mean that the request was free.
        </p>
      </section>
      <section>
        <h2>Search outcomes and availability.</h2>
        <p>
          The service helps identify and address supported SEO problems. It does
          not guarantee indexing, rankings, inclusion in AI answers, citations,
          traffic, conversions or revenue. Search engines, answer engines and
          deployment platforms make independent decisions.
        </p>
        <p>
          This is an early public release. The service may be interrupted,
          changed or unavailable. Keep independent backups and do not rely on
          the service as the sole way to protect a website or meet a legal
          obligation.
        </p>
      </section>
      <section>
        <h2>Disconnecting, suspension and data requests.</h2>
        <p>
          You can disconnect GitHub or revoke the App installation to stop
          future repository access. Previously published commits and pull
          requests remain in GitHub unless separately removed there. Data access
          and deletion requests follow the process in the privacy notice.
        </p>
        <p>
          Access may be restricted or suspended for abuse, security reasons,
          lack of required permissions or service operation. Where practical, an
          explanation can be provided. The open-source repository’s software
          licence is separate from these hosted-service terms.
        </p>
      </section>
      <section>
        <h2>Limitations and changes.</h2>
        <p>
          To the extent permitted by applicable law, the service is provided as
          available, without a guarantee of uninterrupted operation or a
          particular business outcome. Nothing in these terms excludes rights or
          liabilities that cannot lawfully be excluded. No governing
          jurisdiction or arbitration requirement is added by these terms.
        </p>
        <p>
          These terms may be updated as the service changes. The effective date
          identifies the current version. Material changes may also be
          communicated through the service.
        </p>
        <Link className="text-link" href="/contact">
          Questions about these terms? →
        </Link>
      </section>
    </EditorialPage>
  );
}
