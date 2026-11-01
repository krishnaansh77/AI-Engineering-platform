const HOP_BY_HOP_HEADERS = new Set([
  "connection",
  "content-length",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
]);

function readBody(request) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    request.on("data", (chunk) => chunks.push(Buffer.from(chunk)));
    request.on("end", () => resolve(Buffer.concat(chunks)));
    request.on("error", reject);
  });
}

function targetUrl(request) {
  const origin = process.env.DJANGO_API_URL;
  if (!origin) throw new Error("DJANGO_API_URL is not configured in Vercel.");
  const incoming = String(request.url || "/api");
  const suffix = incoming.startsWith("/api") ? incoming.slice(4) : incoming;
  return new URL(`/api${suffix || "/"}`, origin.endsWith("/") ? origin : `${origin}/`);
}

export default async function handler(request, response) {
  try {
    const method = String(request.method || "GET").toUpperCase();
    const headers = Object.fromEntries(
      Object.entries(request.headers || {}).filter(([name]) => !HOP_BY_HOP_HEADERS.has(name.toLowerCase())),
    );
    const body = method === "GET" || method === "HEAD" ? undefined : await readBody(request);
    const upstream = await fetch(targetUrl(request), { method, headers, body, redirect: "manual" });

    response.status(upstream.status);
    upstream.headers.forEach((value, name) => {
      if (!HOP_BY_HOP_HEADERS.has(name.toLowerCase())) response.setHeader(name, value);
    });
    response.send(Buffer.from(await upstream.arrayBuffer()));
  } catch (error) {
    response.status(502).json({ detail: error instanceof Error ? error.message : "API proxy failed." });
  }
}
