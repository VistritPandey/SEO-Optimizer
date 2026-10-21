import { site } from "@/lib/site";

export const dynamic = "force-static";
export function GET() {
  const text = `# Your Optimiser

> An autonomous SEO agent for ongoing website care. It checks relevant website changes, prepares evidence-backed fixes in GitHub pull requests and verifies the served website after deployment.

Official website: ${site.url}

## Product
- [Overview](${site.url}/): What the product does and the current free plan.
- [How it works](${site.url}/how-it-works): Connect GitHub, inspect relevant changes, review a proposed fix and verify deployment.
- [SEO and AI search](${site.url}/seo-and-ai-search): Technical search foundations, consistent facts and visibility measurement.
- [Continuous SEO guide](${site.url}/guides/continuous-seo): An original practical guide using the product's website-change workflow.

## Journal
- [Journal](${site.url}/blog): Original practical articles on autonomous SEO and website care.
- [What is an autonomous SEO agent?](${site.url}/blog/what-is-an-autonomous-seo-agent): Responsibilities, controls and a real local repair example.
- [SEO release checklist](${site.url}/blog/seo-checklist-after-a-website-update): Checks for relevant website updates.
- [SEO and GEO priorities](${site.url}/blog/seo-and-geo-what-to-fix-first): Discovery, clear facts and separate outcome measurement.

## Trust and policies
- [Security and control](${site.url}/security): Repository access, review boundaries and data handling.
- [Privacy](${site.url}/privacy): Account, repository, model-processing and service-log information.
- [Terms](${site.url}/terms): Service conditions and responsibilities.
- [Contact](${site.url}/contact): Support and requests for a private contact channel.

## Accurate product facts
- The hosted integration is GitHub. Other source-control and CMS integrations are not currently offered.
- The current free tier allows up to 3 connected websites and 100 audit/follow-up jobs per month, shared across the workspace.
- Hosted fixes are proposed in pull requests for owner review. A proposed fix, a merge, a deployment and a verified fix are different states.
- Healthy changes may result in no edit. Unsupported business claims require owner evidence.
- Checks focus on confirmed technical and content issues. Search indexing, rankings, AI citations, traffic and conversions are not guaranteed.
- The interactive landing-page example is a fictional store illustrating a repair workflow. It is not a customer result or live audit.
- This file is a human-readable product index. It grants no access to private workspaces and is not a ranking mechanism or crawler-control policy. See /robots.txt for crawl directives.
`;
  return new Response(text, {
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
}
