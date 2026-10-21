export type ArticleSection = {
  id: string;
  title: string;
  paragraphs: string[];
  bullets?: string[];
  source?: { label: string; url: string };
};

export type Article = {
  slug: string;
  category: string;
  title: string;
  description: string;
  takeaway: string;
  image: string;
  imageAlt: string;
  published: string;
  sections: ArticleSection[];
};

export const articles: Article[] = [
  {
    slug: "what-is-an-autonomous-seo-agent",
    category: "THE AGENT EXPLAINED",
    title: "What is an autonomous SEO agent?",
    description: "An audit tells you what needs attention. An autonomous SEO agent follows the work through: inspect, repair, test and verify. Here is what that means in practice.",
    takeaway: "Autonomy means the agent can move work forward within your rules. It does not mean every finding deserves an edit, or every proposed change should skip review.",
    image: "/editorial/continuous-care.webp",
    imageAlt: "A forest-green paper loop passing through three ivory frames, with a small aligned block at its centre.",
    published: "2026-10-20",
    sections: [
      {
        id: "from-report-to-action",
        title: "From a report to a completed task",
        paragraphs: [
          "An autonomous SEO agent is software that can inspect a website, investigate supported search problems, prepare changes and check the result without needing a separate instruction for every step. Its useful output is a traceable task: what was observed, what changed and what was verified.",
          "Consider a homepage redesign that leaves the main collection button pointing to a deleted URL. A report can list a broken link. An agent can follow the destination, find the working collection, inspect the source, propose a small patch and run the project’s checks. After the patch is approved and deployed, it can revisit the served page.",
          "That last step matters. A source edit can be correct while a deployment still serves the old version. The task should remain open until the website evidence catches up with the code.",
        ],
      },
      {
        id: "what-runs-by-itself",
        title: "What happens automatically, and what stays with you?",
        paragraphs: [
          "In Your Optimiser’s hosted workflow, a monitored repository update can trigger the investigation. The agent focuses on relevant files and pages, evaluates evidence, stages a permitted repair, runs configured checks and opens a pull request when justified. Your team reviews and merges it. Deployment checks then establish whether the repair reached the site.",
          "The distinction is deliberate: autonomous investigation and preparation can coexist with human publication review. Local installations have their own action policy. Enabling a model does not grant it permission to rewrite every file, publish unsupported content or change intentional private pages.",
        ],
        bullets: [
          "You choose the repository, monitored branch and permitted directories.",
          "You supply business facts that cannot safely be inferred from code.",
          "The application enforces publication permissions and verification requirements.",
          "Missing evidence stays a dependency rather than becoming a fabricated fix.",
        ],
      },
      {
        id: "real-example",
        title: "What we observed in a recorded repair",
        paragraphs: [
          "Our 52-second demo condenses a real local run on a fictional lighting shop. The fixture had four confirmed defects: a missing description, a broken collection link, conflicting canonical declarations and incorrect product offer data. The agent read two source files, proposed patches and ran the fixture’s checks in an isolated environment.",
          "The worker rechecked the served pages and recorded four resolved defects with no regressions detected in that audit. The private preview and crawler preferences stayed unchanged. A repeat audit created no new commit. A subsequent docs-only merge produced no inference request because it affected no configured website route.",
          "This is evidence of one repair workflow, not a customer case study or an estimate of ranking impact. The demo used local Git. It did not publish a live GitHub pull request, and it did not measure organic traffic or AI citations.",
        ],
        source: { label: "Inspect the recorded repair evidence", url: "https://github.com/YourOptimiser/your-optimiser/blob/main/reports/agent-session.json" },
      },
      {
        id: "healthy-is-an-outcome",
        title: "A healthy page is a successful outcome",
        paragraphs: [
          "An agent that edits something on every run is creating work, not necessarily value. A new background colour may leave the title, links and public content intact. A sensible result is to record the relevant checks and stop. A shared template change, on the other hand, can justify looking beyond the edited file because many pages inherit its output.",
          "This is why change scope and periodic checks belong together. Events make the workflow timely. Reconciliation helps catch missed events and website changes outside the repository. Neither should turn into repeated model calls for an unchanged, already verified observation.",
        ],
      },
      {
        id: "what-to-evaluate",
        title: "Evaluate the work, not the activity",
        paragraphs: [
          "Ask for the evidence behind each finding, the actual diff, the checks that ran and the post-deployment observation. A confident explanation is not a test result. A screenshot can reveal an overlapping menu, but it cannot establish whether a search engine indexed the page.",
          "For a trial, include a known defect, a healthy update, an intentionally private page and a failure in the project’s own checks. The agent should repair the defect when policy permits, leave the healthy page alone, preserve privacy and refuse to label a failed check as verified.",
          "Use verified fixes, unnecessary changes, regressions, elapsed time and operating cost to assess the workflow. Track search impressions, clicks, enquiries and AI-answer citations separately. Those outcomes need observations over time and cannot be guaranteed by an autonomous agent.",
        ],
      },
    ],
  },
  {
    slug: "seo-checklist-after-a-website-update",
    category: "PRACTICAL SEO",
    title: "The SEO checks to run after a website update",
    description: "A launch can look perfect and still break discovery. Use this practical checklist to inspect the pages, links and search information your update actually changed.",
    takeaway: "Start with the change and its dependencies. Check the served website after deployment, then distinguish a verified technical repair from a search outcome that needs more time.",
    image: "/editorial/continuous-care.webp",
    imageAlt: "Ivory paper frames joined by a continuous green loop, representing checks that continue after a launch.",
    published: "2026-10-20",
    sections: [
      {
        id: "choose-the-scope",
        title: "1. Name the pages the change can reach",
        paragraphs: [
          "Write a one-sentence release note before opening an audit: “We changed the homepage collection button,” or “We replaced the product-page template.” The first points to a small route set. The second reaches every product using that template. Shared navigation, layout files and routing rules can expand the scope beyond the files in a diff.",
          "Separate production from previews. A preview protected by authentication or an intentional noindex directive is not a search defect merely because it is unavailable to a crawler. Record the intended public pages first so the investigation does not accidentally remove a useful restriction.",
        ],
      },
      {
        id: "responses-and-links",
        title: "2. Follow the links as a visitor would",
        paragraphs: [
          "Open the changed route and its important destinations. Check the response status as well as what appears on screen. In our fictional shop, the homepage rendered correctly, but its primary collection link led to a real 404. Looking at a homepage screenshot alone would miss the failure.",
          "When a URL intentionally moves, check the redirect destination and avoid sending visitors through an unnecessary chain. A redirect that ends at an unrelated homepage can be a poor substitute for preserving the intended page. Keep source links and preferred destination URLs consistent.",
        ],
        bullets: [
          "Test navigation, primary calls to action and links introduced by the update.",
          "Check any redirects at their final destination, not just their first response.",
          "Confirm unknown routes still return a meaningful not-found response.",
        ],
      },
      {
        id: "search-information",
        title: "3. Compare search information with page intent",
        paragraphs: [
          "Inspect the title, description, canonical URL and indexing directives in the served response. Compare these with the intended page and the last known good version. Two canonical declarations naming different destinations deserve investigation; deleting one at random is not a reliable repair.",
          "A page description should accurately summarise that page. It should not invent an offer or become the same generic sentence across a whole site. Google may use page content instead of your description when producing a search snippet, so writing a description does not give you exact control over the search result.",
        ],
        source: { label: "Google’s guidance on search snippets", url: "https://developers.google.com/search/docs/appearance/snippet" },
      },
      {
        id: "rendering-and-facts",
        title: "4. Check rendered content and factual consistency",
        paragraphs: [
          "If the update changes JavaScript rendering, compare the initial response with the rendered page. A heading visible only after a failed request, or navigation that depends on an unavailable script, deserves a closer look. Your build passing does not by itself prove the relevant content is present in the served page.",
          "For products and business pages, compare structured data with what visitors can read. A price of USD 89 on the page and USD 129 in product markup is an inconsistency to resolve using verified facts. Do not fill missing reviews, opening hours, stock or service locations with plausible values.",
        ],
        source: { label: "Google’s structured data quality requirements", url: "https://developers.google.com/search/docs/appearance/structured-data/sd-policies" },
      },
      {
        id: "verify-and-record",
        title: "5. Test the patch, then test the deployment",
        paragraphs: [
          "Run the project’s own build and relevant tests on the proposed files. Review the diff for unrelated changes. Once the approved patch is deployed, fetch the changed page again and repeat the check that established the defect. Record the environment, observation time, revision and any checks that remain unresolved.",
          "Keep a small release record with five fields: changed routes, observed defect, proposed action, source checks and live verification. For a broken collection link, the final evidence is a working collection destination on the configured deployed site, not simply a pull request marked merged.",
          "Then leave healthy pages alone. Search indexing and traffic may change later; a technically correct release check does not prove causation. Treat those metrics as a separate follow-up rather than turning the launch checklist into a promise of better rankings.",
        ],
      },
    ],
  },
  {
    slug: "seo-and-geo-what-to-fix-first",
    category: "SEARCH & AI DISCOVERY",
    title: "SEO and GEO: what should you fix first?",
    description: "Start with accessible pages, clear facts and useful answers. A practical approach to AI-search visibility without magic files, invented citations or misleading scores.",
    takeaway: "Make the business easy to find and understand, then measure each search experience separately. A technical score, a citation and a conversion answer different questions.",
    image: "/editorial/clear-discovery.webp",
    imageAlt: "Layered ivory paper with a green path and an aligned opening, an abstract study of clear discovery.",
    published: "2026-10-20",
    sections: [
      {
        id: "start-with-the-reader",
        title: "Begin with a question your customers actually ask",
        paragraphs: [
          "SEO concerns how people discover and use your pages through search. GEO, short for generative engine optimisation, commonly describes work on visibility in AI-generated answers. Those labels can help organise a project, but they do not tell you which page deserves the next edit.",
          "Start with a real decision: does this service cover my location, does this product fit my needs, or what happens after I connect my repository? A useful page answers the question directly and supplies the evidence behind its answer. Repeating a keyword across several shallow posts gives the reader less help than one complete explanation.",
          "For Your Optimiser, that means explaining what runs autonomously and where review remains in the workflow. Publishing our real repair method is more informative than claiming an unexplained “AI visibility score.” The same principle applies to your own product: explain what it does, where it works and what it cannot establish.",
        ],
      },
      {
        id: "fix-access-first",
        title: "Resolve access and page integrity before adding more copy",
        paragraphs: [
          "A helpful explanation cannot do much for a visitor who follows a broken link. Check the public URL, important internal links, preferred URL declarations and whether the intended content reaches the served page. Preserve private areas. Crawl access and indexing are distinct: permitting a fetch is not proof that a page is indexed.",
          "An AI-answer result also depends on the engine and retrieval context. A page that is available to one crawler is not automatically used by every answer system. Avoid a blanket “allow all bots” change when a site owner has deliberately chosen a crawler policy.",
        ],
        source: { label: "Google’s explanation of robots.txt and its limits", url: "https://developers.google.com/search/docs/crawling-indexing/robots/intro" },
      },
      {
        id: "google-specific-guidance",
        title: "For Google, special AI files are not the starting point",
        paragraphs: [
          "Google’s current guidance for its generative Search features points back to established SEO and useful, distinctive content. It does not recommend llms.txt or special AI markup as a way to improve visibility in Google. That is a Google-specific statement, not a universal claim about every consumer of an llms.txt file.",
          "Our own llms.txt is a readable index of product facts and public links. We do not treat its presence as a ranking improvement or use it to control crawlers. Likewise, article markup describes an article; it cannot turn unsupported copy into trustworthy evidence or guarantee an AI citation.",
        ],
        source: { label: "Google’s generative AI search optimisation guide", url: "https://developers.google.com/search/docs/fundamentals/ai-optimization-guide" },
      },
      {
        id: "provide-evidence",
        title: "Make your claims specific enough to check",
        paragraphs: [
          "Add original material where it helps the decision: a documented repair, a real product specification, a clear explanation of your process, or a service limitation. Keep business identity, pricing and availability consistent across relevant pages. If those facts change, update the explanation and its supporting records together.",
          "Structure the page for readers. Use a descriptive heading, a direct introduction and sections that answer the next likely questions. Explain the method and limits of any result. A fictional demonstration should say it is fictional; a local test should not be presented as a customer’s production improvement.",
          "Do not pad a page to reach an arbitrary length. A blog is a publishing format, not a ranking feature. Before creating another article, ask whether it solves a different reader problem or only restates what an existing page already covers.",
        ],
        source: { label: "Google’s people-first content guidance", url: "https://developers.google.com/search/docs/fundamentals/creating-helpful-content" },
      },
      {
        id: "measure-with-care",
        title: "Keep repair, visibility and value in separate columns",
        paragraphs: [
          "A verified repair answers whether a known technical defect was resolved. Search impressions and clicks describe search exposure and visits. An AI citation tells you that an answer referenced a source in an observed response. An enquiry or purchase is a business event. None of these is a replacement for the others.",
          "For an AI-answer experiment, save the engine, question, date, whether retrieval occurred, cited URL and whether the answer represented the page accurately. Repeat the observation and keep cases with no citation. Record any changes made between observations so a surprising answer is not mistaken for a stable trend.",
          "Prioritise a confirmed broken journey ahead of a speculative optimisation trick. Once the fundamentals work, use your visibility observations to decide which explanations need more substance. That gives both readers and your team a reason for the next edit.",
        ],
      },
    ],
  },
];

export function readingMinutes(article: Article) {
  const words = [article.description, ...article.sections.flatMap(s => [s.title, ...s.paragraphs, ...(s.bullets ?? [])])].join(" ").split(/\s+/).length;
  return Math.max(1, Math.ceil(words / 220));
}
