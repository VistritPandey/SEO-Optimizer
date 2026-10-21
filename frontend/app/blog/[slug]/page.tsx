import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { ArticleLayout } from "@/components/ArticleLayout";
import { articles, readingMinutes } from "@/lib/articles";
import { pageMetadata, site } from "@/lib/site";

export const dynamicParams = false;
export function generateStaticParams() { return articles.map(article => ({slug:article.slug})); }

export async function generateMetadata({params}:{params:Promise<{slug:string}>}):Promise<Metadata> {
  const {slug}=await params;
  const article=articles.find(item=>item.slug===slug);
  if(!article) notFound();
  const metadata=pageMetadata(article.title,article.description,`/blog/${slug}`);
  return {...metadata,openGraph:{...metadata.openGraph,type:"article",publishedTime:article.published,modifiedTime:article.published,images:[{url:`${site.url}${article.image}`,width:1440,height:960,alt:article.imageAlt}]},twitter:{card:"summary_large_image",title:article.title,description:article.description,images:[`${site.url}${article.image}`]}};
}

export default async function Page({params}:{params:Promise<{slug:string}>}) {
  const {slug}=await params;
  const article=articles.find(item=>item.slug===slug);
  if(!article) notFound();
  return <ArticleLayout {...article} path={`/blog/${slug}`} minutes={readingMinutes(article)} contents={article.sections}>
    {article.sections.map(section=><section id={section.id} key={section.id}>
      <h2>{section.title}</h2>
      {section.paragraphs.map(paragraph=><p key={paragraph}>{paragraph}</p>)}
      {section.bullets && <ul>{section.bullets.map(bullet=><li key={bullet}>{bullet}</li>)}</ul>}
      {section.source && <p className="article-source">Source: <a href={section.source.url} target="_blank" rel="noopener noreferrer">{section.source.label} ↗</a></p>}
    </section>)}
    {slug==="what-is-an-autonomous-seo-agent" && <aside className="article-note"><strong>Watch the recorded example.</strong><p>The silent demo shows the actual patch excerpts and checks from the fictional shop described here.</p><Link href="/how-it-works#agent-demo" className="text-link">Watch the agent work →</Link></aside>}
  </ArticleLayout>;
}
