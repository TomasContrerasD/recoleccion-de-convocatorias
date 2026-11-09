import NextAuth from "next-auth";
import GoogleProvider from "next-auth/providers/google";
import { isAllowedEmail } from "../../../lib/authPolicy";

const handler = NextAuth({
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
  ],
  callbacks: {
    async signIn({ user, profile }) {
      return !!profile && "email_verified" in profile && profile.email_verified === true && isAllowedEmail(
        user.email,
        process.env.AUTH_ALLOWED_EMAILS,
        process.env.AUTH_ALLOWED_DOMAINS,
      );
    },
  },
  pages: {
    signIn: '/login', 
  }
});

export { handler as GET, handler as POST };
