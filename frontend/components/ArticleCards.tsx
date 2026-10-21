import Image from "next/image";
import Link from "next/link";
import { articles, readingMinutes } from "@/lib/articles";

export function ArticleCards() {
  return (
    <div className="journal-cards">
      {articles.map((article, index) => (
        <article key={article.slug} className="journal-card">
          <Link
            href={`/blog/${article.slug}`}
            className="journal-card-image"
            aria-label={`Read ${article.title}`}
          >
            <Image
              src={article.image}
              alt=""
              width={1440}
              height={960}
              sizes="(max-width: 760px) 88vw, 30vw"
            />
            <span aria-hidden="true">0{index + 1} ↗</span>
          </Link>
          <div className="journal-card-copy">
            <span className="eyebrow">{article.category}</span>
            <h3>
              <Link href={`/blog/${article.slug}`}>{article.title}</Link>
            </h3>
            <p>{article.description}</p>
            <div className="journal-card-meta">
              <span>{readingMinutes(article)} min read</span>
              <time dateTime={article.published}>20 October 2026</time>
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}
