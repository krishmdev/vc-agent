import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // `make build-offline` builds into .next-offline so it doesn't overwrite a live build;
  // NEXT_PUBLIC_VC_AGENT_MODE is inlined at build time.
  distDir: process.env.NEXT_DIST_DIR || ".next",
};

export default nextConfig;
