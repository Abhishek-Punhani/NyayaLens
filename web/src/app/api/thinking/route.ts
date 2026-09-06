import { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const sessionId = searchParams.get("session_id");

  if (!sessionId) {
    return new Response("Missing session_id query parameter", { status: 400 });
  }

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
  const backendStreamUrl = `${backendUrl}/api/session/${sessionId}/thinking-stream`;

  try {
    const backendResponse = await fetch(backendStreamUrl, {
      headers: {
        Accept: "text/event-stream",
      },
      cache: "no-store",
    });

    if (!backendResponse.ok) {
      return new Response(`Backend returned ${backendResponse.status}`, {
        status: backendResponse.status,
      });
    }

    // Stream SSE directly to the browser client
    return new Response(backendResponse.body, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive",
      },
    });
  } catch (error: any) {
    return new Response(`Failed to connect to backend SSE: ${error?.message}`, {
      status: 502,
    });
  }
}
