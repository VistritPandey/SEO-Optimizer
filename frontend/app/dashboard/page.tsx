import { Dashboard } from "@/components/Dashboard";
import { MotionProvider } from "@/components/Motion";
import "./workspace.css";
export const metadata = {
  title: "Workspace",
  robots: { index: false, follow: false },
};
export default function Page() {
  return (
    <MotionProvider>
      <Dashboard />
    </MotionProvider>
  );
}
