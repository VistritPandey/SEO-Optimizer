import type { Metadata } from "next";

export const site = {
  name: "Your Optimiser",
  url: "https://youroptimiser.com",
  description:
    "Your autonomous SEO agent. Monitor website changes, investigate supported issues, prepare tested GitHub fixes and verify the deployed result.",
  repository: "https://github.com/YourOptimiser/your-optimiser",
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
  "/blog",
  "/blog/what-is-an-autonomous-seo-agent",
  "/blog/seo-checklist-after-a-website-update",
  "/blog/seo-and-geo-what-to-fix-first",
];

export function pageMetadata(
  title: string,
  description: string,
  path: string,
): Metadata {
  return {
    title,
    description,
    authors: [{ name: site.name, url: site.url }],
    creator: site.name,
    publisher: site.name,
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

export function articleMetadata({
  title,
  description,
  path,
  image,
  imageAlt,
  published,
  updated,
}: {
  title: string;
  description: string;
  path: string;
  image: string;
  imageAlt: string;
  published: string;
  updated?: string;
}): Metadata {
  const metadata = pageMetadata(title, description, path);
  return {
    ...metadata,
    openGraph: {
      ...metadata.openGraph,
      type: "article",
      authors: [site.url],
      publishedTime: published,
      modifiedTime: updated ?? published,
      images: [
        { url: `${site.url}${image}`, width: 1440, height: 960, alt: imageAlt },
      ],
    },
    twitter: {
      ...metadata.twitter,
      images: [`${site.url}${image}`],
    },
  };
}
