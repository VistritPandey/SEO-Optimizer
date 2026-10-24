import { ConnectionsWorkspace } from "@/components/ConnectionsWorkspace";
import { MotionProvider } from "@/components/Motion";
import "../workspace.css";
export const metadata = {
  title: "Connections",
  robots: { index: false, follow: false },
};
export default async function Page({
  searchParams,
}: {
  searchParams: Promise<{ project?: string }>;
}) {
  const query = await searchParams;
  return (
    <MotionProvider>
      <ConnectionsWorkspace projectId={query.project} />
    </MotionProvider>
  );
}
