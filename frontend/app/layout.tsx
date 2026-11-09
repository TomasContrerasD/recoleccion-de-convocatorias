import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Link from "next/link";
import { Providers } from "./Providers";
import PerfilUsuario from "./components/PerfilUsuario";

const inter = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "Recolector de convocatorias",
  description: "Explora convocatorias de organismos internacionales y evalúa su encaje para tu empresa.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body className={`${inter.variable} m-0`}>
        <Providers>

          {/* ── TOP NAV ── */}
          <header className="fixed top-0 left-0 right-0 z-50 h-[60px] flex items-center bg-white/90 backdrop-blur-[16px] border-b border-app-border shadow-sm">

            {/* Center: Logo + nav */}
            <div className="absolute left-1/2 -translate-x-1/2 flex flex-col items-center gap-[5px]">
              <Link href="/" className="no-underline">
                <span className="font-[var(--font-inter)] text-[1rem] font-extrabold tracking-[0.1em] uppercase leading-none">
                  <span className="text-app-text">Convocatorias</span>
                </span>
              </Link>
              <nav className="flex items-center gap-1">
                <Link href="/" className="nav-link">Inicio</Link>
              </nav>
            </div>

            {/* Right: user profile */}
            <div className="ml-auto pr-8">
              {process.env.NODE_ENV !== "development" && <PerfilUsuario />}
            </div>
          </header>

          {/* ── MAIN ── */}
          <main className="pt-[60px] min-h-screen">
            {children}
          </main>

          {/* ── FOOTER ── */}
          <footer
            style={{
              borderTop: "1px solid rgba(0,0,0,0.08)",
              background: "rgba(255,255,255,0.82)",
              backdropFilter: "blur(12px)",
              padding: "20px 40px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              flexWrap: "wrap",
              gap: "8px",
            }}
          >
            <span style={{ fontSize: "0.72rem", color: "#9ca3af", fontFamily: "var(--font-inter)" }}>
              © {new Date().getFullYear()} Recolector de convocatorias.
            </span>
            <span style={{ fontSize: "0.72rem", color: "#9ca3af", fontFamily: "var(--font-inter)" }}>
              Creado por <span style={{ color: "#6b7280", fontWeight: 600 }}>Tomás Contreras</span>
            </span>
          </footer>

        </Providers>
      </body>
    </html>
  );
}
