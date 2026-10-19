import type { MetadataRoute } from "next";
import { publicPages, site } from "@/lib/site";
export default function sitemap(): MetadataRoute.Sitemap {
  return publicPages.map((path) => ({ url: new URL(path, site.url).href }));
}
