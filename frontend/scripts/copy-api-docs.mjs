// Копирует Swagger UI из node_modules в dist/api-docs: документация API без внешних CDN.
import { cpSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const src = dirname(require.resolve("swagger-ui-dist/package.json"));
const out = "dist/api-docs";
mkdirSync(out, { recursive: true });
for (const f of ["swagger-ui-bundle.js", "swagger-ui.css"]) cpSync(join(src, f), join(out, f));
cpSync("api-docs", out, { recursive: true });
console.log("api-docs -> " + out);
