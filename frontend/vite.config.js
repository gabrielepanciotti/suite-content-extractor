import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // @suite/design-system is linked from the Life packages, so its Radix
  // dependencies resolve React from Life/node_modules — a second copy, whose
  // hooks blow up with "Cannot read properties of null". One React only.
  resolve: { dedupe: ["react", "react-dom"] },
  server: {
    port: 3387,
    proxy: {
      "/api": process.env.VITE_BACKEND_PROXY_TARGET || "http://localhost:10053",
    },
  },
  // Il servizio systemd serve la versione COSTRUITA (`npm run serve`): usa
  // una frazione della memoria del server di sviluppo e non viene fermato
  // dal supervisore quando la RAM libera scende. Stesse porta e stesso proxy.
  preview: {
    port: 3387,
    host: true,
    allowedHosts: true,
    proxy: {
      "/api": process.env.VITE_BACKEND_PROXY_TARGET || "http://localhost:10053",
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    // Vitest externalises node_modules by default, so the linked packages
    // would be loaded by Node and resolve their own React copy, bypassing
    // the dedupe above. Inlining them puts them back under Vite resolution.
    server: { deps: { inline: [/@suite\//, /@radix-ui\//] } },
  },
});
