export function isAllowedEmail(
  email: string | null | undefined,
  allowedEmails = "",
  allowedDomains = "",
): boolean {
  const normalized = email?.trim().toLowerCase();
  if (!normalized || !normalized.includes("@")) return false;
  const emails = allowedEmails.split(",").map(value => value.trim().toLowerCase()).filter(Boolean);
  const domains = allowedDomains.split(",").map(value => value.trim().toLowerCase().replace(/^@/, "")).filter(Boolean);
  return emails.includes(normalized) || domains.includes(normalized.split("@")[1]);
}
