import type { Metadata } from "next";
import { ResetPasswordPage } from "@/features/auth/LinkPages";

export const metadata: Metadata = {
  title: "Choose a new password · JSAN Road Event Intelligence",
  // A link with a single-use token: never indexed.
  robots: { index: false, follow: false },
};

export default function ResetPassword() {
  return <ResetPasswordPage />;
}
