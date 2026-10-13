import type {MetadataRoute} from 'next';
export default function sitemap(): MetadataRoute.Sitemap {
  const site = process.env.NEXT_PUBLIC_SITE_URL;
  return site ? [{url: new URL('/', site).href}] : [];
}
