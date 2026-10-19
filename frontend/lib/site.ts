import type { Metadata } from "next";

export const site = {
  name: "Your Optimiser",
  url: "https://youroptimiser.com",
  description:
    "Ongoing SEO care for a website that keeps changing. Your AI agent checks updates, prepares focused fixes in GitHub and verifies them after deployment.",
  repository: "https://github.com/YourOptimiser/SEO-Optimizer",
  supportEmail: "support@youroptimiser.com",
};

export const publicPages = [
  "/",
  "/how-it-works",
  "/seo-and-ai-search",
  "/guides/continuous-seo",
  "/security",
  "/contact",
  "/privacy",
  "/terms",
];

export function pageMetadata(
  title: string,
  description: string,
  path: string,
): Metadata {
  return {
    title,
    description,
    alternates: { canonical: path },
    openGraph: {
      type: "website",
      siteName: site.name,
      title: `${title} · ${site.name}`,
      description,
      url: path,
      images: [
        {
          url: `${site.url}/opengraph-image`,
          width: 1200,
          height: 630,
          alt: site.name,
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title: `${title} · ${site.name}`,
      description,
      images: [`${site.url}/opengraph-image`],
    },
  };
}
