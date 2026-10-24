import { notFound } from "next/navigation";
import { ConnectionsWorkspace } from "@/components/ConnectionsWorkspace";
import { MotionProvider } from "@/components/Motion";
import catalog from "@/lib/connection-catalog.json";
import "../../workspace.css";
export const metadata = {
  title: "Connection",
  robots: { index: false, follow: false },
};
export default async function Page({
  params,
  searchParams,
}: {
  params: Promise<{ platform: string }>;
  searchParams: Promise<{ project?: string }>;
}) {
  const [{ platform }, query] = await Promise.all([params, searchParams]);
  if (
    platform !== "github" &&
    !catalog.some((item) => item.platform === platform)
  )
    notFound();
  return (
    <MotionProvider>
      <ConnectionsWorkspace
        key={`${platform}:${query.project || ""}`}
        platform={platform}
        projectId={query.project}
      />
    </MotionProvider>
  );
}
