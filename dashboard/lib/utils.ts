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

import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function isAdmin(userId?: string | null) {
  if (!userId) return false;
  const adminIds = (process.env.NEXT_PUBLIC_ADMIN_IDS || "").split(",");
  return adminIds.includes(userId);
}
