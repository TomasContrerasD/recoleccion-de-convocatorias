import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async redirects() {
    return [
      {
        source: "/otros-multiuso",
        destination: "/",
        permanent: true,
      },
      {
        source: "/otros-multiuso/scraping14_convocatorias_bancarias",
        destination: "/",
        permanent: true,
      },
    ];
  },
};

export default nextConfig;
