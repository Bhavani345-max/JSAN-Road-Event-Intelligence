import type { Metadata } from "next";
import LoginPage from "@/features/auth/LoginPage";

export const metadata: Metadata = {
  title: "Sign in · JSAN Road Event Intelligence",
  description: "Secure sign-in to the JSAN Road Event Intelligence workspace.",
};

export default function SignIn() {
  return <LoginPage />;
}
