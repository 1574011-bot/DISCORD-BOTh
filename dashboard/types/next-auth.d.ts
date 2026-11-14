/**
 * ╔══════════════════════════════════════════════════════════════════╗
 * ║                                                                  ║
 * ║   UND — All In One                                               ║
 * ║                                                                  ║
 * ║                                                                  ║
 * ║   © 2026 KURAPIKA — All Rights Reserved                          ║
 * ║   Built & owned by Kurapika                                      ║
 * ╚══════════════════════════════════════════════════════════════════╝
 */

import NextAuth, { DefaultSession } from "next-auth";

declare module "next-auth" {
  interface Session {
    accessToken?: string;
    user: {
      id: string;
    } & DefaultSession["user"];
  }
}
