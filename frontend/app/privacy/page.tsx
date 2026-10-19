import Link from "next/link";
import { EditorialPage } from "@/components/EditorialPage";
import { pageMetadata } from "@/lib/site";

export const metadata = pageMetadata(
  "Privacy notice",
  "How Your Optimiser handles account information, repository access, website evidence, AI processing and service logs.",
  "/privacy",
);

export default function Page() {
  return (
    <EditorialPage
      eyebrow="PRIVACY NOTICE · EFFECTIVE 19 OCTOBER 2026"
      title={
        <>
          Know what you share.
          <br />
          <em>Know why it’s needed.</em>
        </>
      }
      intro="This notice covers the hosted Your Optimiser service at youroptimiser.com. The project maintainers operate the service. A self-hosted installation is controlled by its own operator and configuration."
    >
      <section>
        <h2>Information the service processes.</h2>
        <p>
          Account information includes your email address, Firebase account
          identifier and authentication status. Workspace information includes
          connected repository identifiers, website URLs, project settings,
          business facts and goals you provide, quotas and activity records.
        </p>
        <p>
          To perform an audit or repair, the service may process relevant source
          files, public page content, audit evidence, findings, proposed edits,
          check results, optional screenshots and pull request or deployment
          information. GitHub connection grants and installation identifiers
          support authorised repository access.
        </p>
        <p>
          Operational records can include request times, network addresses,
          errors and service activity. Authentication and hosting providers also
          process information needed to run their services.
        </p>
      </section>
      <section>
        <h2>Why this information is used.</h2>
        <p>
          The information supports sign-in, workspace isolation, repository
          connection, SEO checks, proposed fixes, verification, abuse
          prevention, troubleshooting and usage limits. Project facts help the
          agent avoid unsupported changes.
        </p>
        <p>
          The current application does not include advertising trackers or a
          third-party marketing analytics SDK. That does not mean the service is
          anonymous: authentication, infrastructure and support activity still
          involve data processing.
        </p>
      </section>
      <section>
        <h2>Providers and AI processing.</h2>
        <p>
          The hosted service uses Google Cloud and Firebase for hosting,
          authentication, storage, operational services and logs, and GitHub for
          repository authorisation, code changes and pull requests. A
          third-party AI provider processes relevant task inputs to generate
          assessments and proposed edits; inputs can include code, page content,
          project facts and screenshots.
        </p>
        <p>
          AI providers may change. Their applicable terms and processing
          settings govern their handling of inputs. We do not promise that every
          possible provider configuration has the same retention or training
          policy. Do not provide unnecessary secrets, sensitive personal
          information or material you lack permission to process.
        </p>
        <a
          className="text-link"
          href="https://firebase.google.com/support/privacy"
          target="_blank"
          rel="noopener noreferrer"
        >
          Firebase’s privacy information ↗
        </a>
      </section>
      <section>
        <h2>Storage and access.</h2>
        <p>
          Workspace records are stored in a Firestore database selected for this
          application. The backend enforces tenant ownership. Service
          credentials are supplied through Secret Manager, and stored
          application credentials and connection grants are encrypted by the
          backend. Authorised operators can access systems when needed to
          operate and support the service.
        </p>
        <p>
          These measures reduce risk; they are not a promise that every security
          incident can be prevented. Data may be processed in countries where
          infrastructure and AI providers operate. We do not promise that all
          processing stays in a single region.
        </p>
      </section>
      <section>
        <h2>Cookies and browser storage.</h2>
        <p>
          Firebase Authentication uses browser storage to maintain your sign-in
          state. The service may use session information for account and
          authorisation flows. You can clear browser storage or sign out;
          clearing it does not delete server-side account or workspace records.
        </p>
      </section>
      <section>
        <h2>Retention and your choices.</h2>
        <p>
          Account, project, audit and activity records are retained while
          supporting the service and its operations. There is currently no
          universal automatic deletion period for all record types.
          Infrastructure providers manage operational logs and temporary
          artifacts according to their configured lifecycles.
        </p>
        <p>
          Disconnecting GitHub pauses related projects and removes their active
          connection authorisation from the workspace. It does not automatically
          delete historical workspace records or remove commits and pull
          requests already published to GitHub.
        </p>
        <p>
          You can request access, correction or deletion of account and
          workspace data through the private contact process. Requests are
          handled manually and may require identity verification. Applicable law
          may give you additional rights; legal obligations, security needs and
          provider records can affect what can be removed.
        </p>
        <Link className="text-link" href="/contact">
          Request a private contact channel →
        </Link>
      </section>
      <section>
        <h2>Changes to this notice.</h2>
        <p>
          This notice will be updated when the service’s practices change. The
          effective date identifies the current version. Material changes may
          also be communicated through the service. Contact the maintainers with
          questions before connecting data you are unsure about sharing.
        </p>
      </section>
    </EditorialPage>
  );
}
