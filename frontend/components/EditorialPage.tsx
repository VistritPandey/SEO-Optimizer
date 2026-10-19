import Link from "next/link";
import type { ReactNode } from "react";
import { SiteFooter, SiteHeader } from "./SiteChrome";

export function EditorialPage({
  eyebrow,
  title,
  intro,
  children,
  wide = false,
}: {
  eyebrow: string;
  title: ReactNode;
  intro: string;
  children: ReactNode;
  wide?: boolean;
}) {
  return (
    <>
      <SiteHeader />
      <main
        id="main-content"
        className={`editorial-page ${wide ? "editorial-wide" : ""}`}
      >
        <header className="editorial-heading">
          <Link className="back-link" href="/">
            ← Your website, looked after
          </Link>
          <span className="eyebrow">{eyebrow}</span>
          <h1>{title}</h1>
          <p>{intro}</p>
        </header>
        <div className="editorial-content">{children}</div>
      </main>
      <SiteFooter />
    </>
  );
}
