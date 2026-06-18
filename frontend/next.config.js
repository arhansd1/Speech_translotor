/** @type {import('next').NextConfig} */
const nextConfig = {
  // Backend URL injected at build time from Vercel env var
  env: {
    NEXT_PUBLIC_BACKEND_URL: process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000",
  },
}

module.exports = nextConfig
