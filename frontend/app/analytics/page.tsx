import type { Metadata } from "next";
import AnalyticsPage from "@/features/analytics/AnalyticsPage";
import AuthGate from "@/features/auth/AuthGate";

export const metadata: Metadata = {
  title: "Analytics · JSAN Road Event Intelligence",
};

export default function Analytics() {
  return (
    <AuthGate>
      <AnalyticsPage />
    </AuthGate>
  );
}
