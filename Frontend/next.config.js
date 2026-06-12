/** @type {import('next').NextConfig} */
const basePath = process.env.NEXT_PUBLIC_BASE_PATH || '';

const nextConfig = {
  reactStrictMode: true,
  // basePath tells Next.js that all pages/routes live under this prefix.
  // Required when served via a proxy that preserves the path (e.g. Jupyter proxy).
  basePath: basePath,
  assetPrefix: basePath,
  allowedDevOrigins: ['notebooks.amd.com'],
  images: {
    remotePatterns: [],
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8001'}/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;