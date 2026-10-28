import type { Metadata } from "next";
import { VerifyEmailPage } from "@/features/auth/LinkPages";

export const metadata: Metadata = {
  title: "Confirm your email · JSAN Road Event Intelligence",
  // A link with a single-use token: never indexed.
  robots: { index: false, follow: false },
};

export default function VerifyEmail() {
  return <VerifyEmailPage />;
}
