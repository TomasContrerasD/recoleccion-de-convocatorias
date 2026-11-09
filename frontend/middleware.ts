import { withAuth, type NextRequestWithAuth } from "next-auth/middleware";
import { NextResponse, type NextFetchEvent } from "next/server";

const requireAuthentication = withAuth({
  pages: {
    signIn: "/login",
  },
});

export default function middleware(request: NextRequestWithAuth, event: NextFetchEvent) {
  // Local development should work without Google OAuth or session credentials.
  // Production always follows the existing authentication flow.
  if (process.env.NODE_ENV === "development") {
    if (request.nextUrl.pathname === "/login") {
      return NextResponse.redirect(new URL("/", request.url));
    }
    return NextResponse.next();
  }

  return requireAuthentication(request, event);
}

export const config = {
  matcher: ["/((?!api/auth|_next/static|_next/image|favicon.ico).*)"],
};
