/** @type {import('next').NextConfig} */
const nextConfig = {
  // Resolve @google/genai to its browser-compatible web build
  webpack: (config, { isServer }) => {
    if (!isServer) {
      // Tell webpack to use the 'browser' condition for @google/genai
      config.resolve.conditionNames = ["browser", "module", "import", "require", "default"];
    }
    return config;
  },
};

module.exports = nextConfig;
