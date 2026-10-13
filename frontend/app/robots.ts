import type { MetadataRoute } from "next";
export default function robots(): MetadataRoute.Robots {
  const site = process.env.NEXT_PUBLIC_SITE_URL;
  return {
    rules: { userAgent: "*", allow: "/", disallow: "/api/" },
    sitemap: site ? new URL("/sitemap.xml", site).href : undefined,
  };
}
