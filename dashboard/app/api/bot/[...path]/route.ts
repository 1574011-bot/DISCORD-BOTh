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

import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const API_URL = (process.env.API_URL || "http://localhost:8000/api/v1").replace(/\/+$/, "");
const API_KEY = process.env.DASHBOARD_API_KEY;

async function proxy(request: NextRequest, { params }: { params: { path: string[] } }) {
  if (!API_KEY) {
    return NextResponse.json(
      { detail: "DASHBOARD_API_KEY is not set on the dashboard server." },
      { status: 500 }
    );
  }

  const target = `${API_URL}/${params.path.map(encodeURIComponent).join("/")}${request.nextUrl.search}`;
  const hasBody = request.method !== "GET" && request.method !== "HEAD";

  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method: request.method,
      headers: {
        Authorization: `Bearer ${API_KEY}`,
        "Content-Type": request.headers.get("content-type") || "application/json",
      },
      body: hasBody ? await request.text() : undefined,
      cache: "no-store",
    });
  } catch (error) {
    console.error(`[API proxy] ${request.method} ${target} failed:`, error);
    return NextResponse.json({ detail: "The bot API is unreachable." }, { status: 502 });
  }

  const body = await upstream.text();
  return new NextResponse(body, {
    status: upstream.status,
    headers: {
      "Content-Type": upstream.headers.get("content-type") || "application/json",
    },
  });
}

export { proxy as GET, proxy as POST, proxy as PATCH, proxy as PUT, proxy as DELETE };
