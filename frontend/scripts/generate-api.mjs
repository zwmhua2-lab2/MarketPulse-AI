/**
 * Regenerates `src/api/generated.ts` from the current backend OpenAPI contract.
 *
 * `npm run generate:api`
 *
 * The document is exported from the FastAPI application object, so this needs no
 * running backend and no database. The result is deterministic, which is what makes
 * `npm run check:api-drift` a meaningful gate.
 */
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

import { FRONTEND_DIR, GENERATED_PATH, exportOpenApiDocument, generateTypes } from "./openapi-source.mjs";

const scratch = mkdtempSync(path.join(tmpdir(), "marketpulse-openapi-"));

try {
  const documentPath = path.join(scratch, "openapi.json");
  exportOpenApiDocument(documentPath);
  generateTypes(documentPath, GENERATED_PATH);
  console.log(`generated: ${path.relative(FRONTEND_DIR, GENERATED_PATH).split(path.sep).join("/")}`);
} finally {
  rmSync(scratch, { recursive: true, force: true });
}
