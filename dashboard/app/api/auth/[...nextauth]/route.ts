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

import NextAuth from "next-auth";
import { authOptions } from "@/lib/auth";

const handler = NextAuth(authOptions);

export { handler as GET, handler as POST };
