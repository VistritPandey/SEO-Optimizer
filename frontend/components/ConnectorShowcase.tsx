import Link from "next/link";
import { testedPlatforms, coverageLabels } from "@/lib/platforms";
import { PlatformLogo } from "./PlatformLogo";

export function ConnectorBrands() {
  return (
    <ul
      className="connector-brands"
      aria-label="Platforms with hosted repair workflow tests"
    >
      {testedPlatforms
        .filter((platform) => platform.coverage === "hosted")
        .map((platform) => (
          <li key={platform.id}>
            <PlatformLogo platform={platform.id} size={20} />
            <span>{platform.name}</span>
          </li>
        ))}
    </ul>
  );
}

export function ConnectorShowcase() {
  return (
    <section
      className="connector-showcase marketing-section"
      id="connections"
      aria-labelledby="connections-title"
    >
      <div className="customer-intro">
        <div>
          <span className="eyebrow">
            YOUR WEBSITE. YOUR TOOLS. ONE WORKSPACE.
          </span>
          <h2 id="connections-title">
            Works where
            <br />
            <em>your website lives.</em>
          </h2>
        </div>
        <p>
          Connect your code, content and deployment tools. Give the agent access
          to the parts you want it to look after, with a record of what it
          checks and changes.
        </p>
      </div>
      <ul className="connector-showcase-grid">
        {testedPlatforms.map((platform) => (
          <li key={platform.id}>
            <div className="platform-lockup">
              <PlatformLogo platform={platform.id} size={30} />
              <h3>{platform.name}</h3>
            </div>
            <p>{platform.summary}</p>
            <small
              className="platform-coverage"
              data-coverage={platform.coverage}
            >
              {coverageLabels[platform.coverage]}
            </small>
          </li>
        ))}
      </ul>
      <div className="connector-showcase-footnote">
        <p>
          Hosted repair tests cover evidence collection, supported edits and the
          review or restoration workflow. WordPress and WooCommerce were tested
          on a local CMS. Vercel and Netlify tests cover deployment APIs. Draft
          changes still need your normal publication workflow.
        </p>
        <Link href="/login?mode=register" className="text-link">
          Connect your first website ↗
        </Link>
      </div>
    </section>
  );
}
