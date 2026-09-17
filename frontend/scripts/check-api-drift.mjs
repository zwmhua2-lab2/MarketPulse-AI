/**
 * Verifies that the committed OpenAPI types still match the current backend contract.
 *
 * `npm run check:api-drift`
 *
 * Exit 0 means the committed `src/api/generated.ts` is byte-identical to a fresh
 * regeneration from the live backend application, and that the runtime surfaces the
 * frontend depends on are still present. Any other outcome is drift and exits 1.
 */
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

import {
  FRONTEND_DIR,
  GENERATED_PATH,
  exportOpenApiDocument,
  generateTypes,
  normalizeLineEndings,
} from "./openapi-source.mjs";

/** Runtime surfaces the frontend foundation already depends on. */
const REQUIRED_PATHS = ["/api/v1/live", "/api/v1/ready"];

const scratch = mkdtempSync(path.join(tmpdir(), "marketpulse-openapi-drift-"));
const problems = [];

try {
  const documentPath = path.join(scratch, "openapi.json");
  exportOpenApiDocument(documentPath);

  const document = JSON.parse(readFileSync(documentPath, "utf8"));
  const documentPaths = Object.keys(document.paths ?? {});
  for (const required of REQUIRED_PATHS) {
    if (!documentPaths.includes(required)) {
      problems.push(`backend OpenAPI no longer declares ${required}`);
    }
  }

  const regeneratedPath = path.join(scratch, "generated.ts");
  generateTypes(documentPath, regeneratedPath);

  const committed = normalizeLineEndings(readFileSync(GENERATED_PATH, "utf8"));
  const regenerated = normalizeLineEndings(readFileSync(regeneratedPath, "utf8"));
  if (committed !== regenerated) {
    problems.push(
      "src/api/generated.ts is not identical to a fresh regeneration of the current backend OpenAPI",
    );
  }
} finally {
  rmSync(scratch, { recursive: true, force: true });
}

if (problems.length > 0) {
  console.error("OpenAPI drift detected:");
  for (const problem of problems) {
    console.error(`  - ${problem}`);
  }
  console.error(`Run \`npm run generate:api\` in ${FRONTEND_DIR} and commit the result.`);
  process.exit(1);
}

console.log(
  `no OpenAPI drift: ${REQUIRED_PATHS.join(", ")} present; generated.ts matches the backend contract`,
);
