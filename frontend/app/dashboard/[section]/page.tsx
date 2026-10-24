import { notFound } from "next/navigation";
import { Dashboard } from "@/components/Dashboard";
import { MotionProvider } from "@/components/Motion";
import { websiteSections } from "@/lib/website-navigation.mjs";
import "../workspace.css";
export const metadata = {
  title: "Website workspace",
  robots: { index: false, follow: false },
};
export default async function Page({
  params,
  searchParams,
}: {
  params: Promise<{ section: string }>;
  searchParams: Promise<{ project?: string }>;
}) {
  const [{ section }, query] = await Promise.all([params, searchParams]);
  const tab = Object.entries(websiteSections).find(
    ([, slug]) => slug === section,
  )?.[0];
  if (!tab) notFound();
  return (
    <MotionProvider>
      <Dashboard
        key={`${section}:${query.project || ""}`}
        initialTab={tab}
        initialProjectId={query.project}
      />
    </MotionProvider>
  );
}
