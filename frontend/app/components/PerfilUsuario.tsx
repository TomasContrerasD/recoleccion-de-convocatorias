"use client";

import { useSession, signOut } from "next-auth/react";

export default function PerfilUsuario() {
  const { data: session, status } = useSession();
  if (status !== "authenticated" || !session?.user) return null;

  const firstName = session.user.name?.split(" ").slice(0, 2).join(" ") ?? "";

  return (
    <div className="flex items-center gap-3 flex-shrink-0">
      <div className="hidden sm:flex flex-col items-end">
        <span className="text-app-text font-[var(--font-inter)] text-[0.95rem] font-semibold tracking-[0.03em] leading-none">
          {firstName}
        </span>
        <button
          onClick={() => signOut({ callbackUrl: "/login" })}
          className="text-app-muted text-[0.8rem] font-[var(--font-inter)] bg-transparent border-none cursor-pointer p-0 mt-1 hover:text-red-400 transition-colors"
        >
          Cerrar sesión
        </button>
      </div>
      <img
        src={session.user.image ?? ""}
        alt="Perfil"
        width={36}
        height={36}
        className="rounded-full object-cover border border-app-border"
        referrerPolicy="no-referrer"
      />
    </div>
  );
}
