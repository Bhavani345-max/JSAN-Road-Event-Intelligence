import Dashboard from "@/features/dashboard/Dashboard";
import AuthGate from "@/features/auth/AuthGate";

export default function Home() {
  return (
    <AuthGate>
      <Dashboard />
    </AuthGate>
  );
}
