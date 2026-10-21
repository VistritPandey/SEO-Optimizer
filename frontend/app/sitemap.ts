import type { MetadataRoute } from "next";
import { articles } from "@/lib/articles";
import { publicPages, site } from "@/lib/site";
export default function sitemap(): MetadataRoute.Sitemap {
  return publicPages.map((path) => {
    const article = articles.find((item) => `/blog/${item.slug}` === path);
    return {
      url: new URL(path, site.url).href,
      ...(article ? { lastModified: article.published } : {}),
    };
  });
}
