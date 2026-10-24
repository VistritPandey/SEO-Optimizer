import { Dashboard } from "@/components/Dashboard";
import { MotionProvider } from "@/components/Motion";
import "./workspace.css";
export const metadata = {
  title: "Workspace",
  robots: { index: false, follow: false },
};
export default async function Page({
  searchParams,
}: {
  searchParams: Promise<{ project?: string; connect?: string }>;
}) {
  const query = await searchParams;
  return (
    <MotionProvider>
      <Dashboard
        key={`${query.project || ""}:${query.connect || ""}`}
        initialProjectId={query.project}
        initialConnect={query.connect}
      />
    </MotionProvider>
  );
}
