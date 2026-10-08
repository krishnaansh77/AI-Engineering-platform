/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  async rewrites() {
    const configuredBackendUrl = process.env.BACKEND_URL ||
      (process.env.NODE_ENV === "production"
        ? "https://ai-engineering-platform-production.up.railway.app"
        : "http://localhost:8000");
    const backendUrl = configuredBackendUrl.replace(/\/+$/, "");

    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;
