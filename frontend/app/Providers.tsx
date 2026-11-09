"use client";

import { SessionProvider } from "next-auth/react";

export function Providers({ children }: { children: React.ReactNode }) {
  if (process.env.NODE_ENV === "development") return <>{children}</>;
  return <SessionProvider>{children}</SessionProvider>;
}
