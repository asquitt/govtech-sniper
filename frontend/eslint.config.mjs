import nextConfig from "eslint-config-next";

const config = [
  ...nextConfig,
  {
    ignores: ["e2e/**"],
  },
  {
    rules: {
      "react-hooks/set-state-in-effect": "off",
    },
  },
];

export default config;
