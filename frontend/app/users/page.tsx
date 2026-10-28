import type { Metadata } from "next";
import AuthGate from "@/features/auth/AuthGate";
import UserManagement from "@/features/users/UserManagement";

export const metadata: Metadata = {
  title: "User management · JSAN Road Event Intelligence",
};

export default function Users() {
  return (
    <AuthGate>
      <UserManagement />
    </AuthGate>
  );
}
