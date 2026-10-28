import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { linkToken, registrationProblem, strongPasswordProblem } from "./accountApi";

const DOMAINS = ["jsan.example"];
const form = (changes: Partial<{ name: string; email: string; password: string; confirmation: string }> = {}) => ({
  name: "Pavan Kumar",
  email: "pavan@jsan.example",
  password: "long enough phrase 7",
  confirmation: "long enough phrase 7",
  ...changes,
});

describe("registration form (decision 0045)", () => {
  it("accepts a full, company, strong request", () => {
    expect(registrationProblem(form(), DOMAINS)).toBeNull();
    expect(registrationProblem(form({ email: " Pavan@JSAN.example " }), DOMAINS)).toBeNull();
  });

  it("asks for a name and a company address", () => {
    expect(registrationProblem(form({ name: "  " }), DOMAINS)).toBe("Enter your full name.");
    expect(registrationProblem(form({ email: "pavan" }), DOMAINS)).toBe("Enter your company email address.");
    expect(registrationProblem(form({ email: "pavan@gmail.com" }), DOMAINS)).toBe(
      "Use your company email address (@jsan.example).",
    );
  });

  it("refuses weak or mismatched passwords", () => {
    expect(registrationProblem(form({ password: "short", confirmation: "short" }), DOMAINS)).toMatch("at least 8");
    expect(registrationProblem(form({ password: "password123", confirmation: "password123" }), DOMAINS)).toMatch("too easy");
    expect(registrationProblem(form({ password: "pavan-rules-99", confirmation: "pavan-rules-99" }), DOMAINS)).toMatch("email's name");
    expect(registrationProblem(form({ confirmation: "something else 1" }), DOMAINS)).toBe("The two passwords are not the same.");
  });

  it("refuses the very same common passwords as the API", () => {
    const api = readFileSync(
      fileURLToPath(new URL("../../../backend/app/services/account_service.py", import.meta.url)),
      "utf8",
    );
    const block = api.slice(api.indexOf("COMMON_PASSWORDS = frozenset({"), api.indexOf("})", api.indexOf("COMMON_PASSWORDS")));
    const listed = [...block.matchAll(/"([^"]+)"/g)].map((match) => match[1]);
    expect(listed.length).toBeGreaterThan(10);
    for (const password of listed) expect(strongPasswordProblem(password)).not.toBeNull();
    expect(strongPasswordProblem("aaaaaaaaaa")).toMatch("too easy"); // fewer than 4 different characters
  });
});

describe("emailed links", () => {
  it("read their token from the address", () => {
    expect(linkToken("?token=abc-DEF_123")).toBe("abc-DEF_123");
    expect(linkToken("")).toBeNull();
    expect(linkToken(`?token=${"x".repeat(201)}`)).toBeNull();
  });
});
