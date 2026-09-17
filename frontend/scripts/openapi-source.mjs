/**
 * Shared mechanics for the OpenAPI generation pipeline.
 *
 * `generate:api` and `check:api-drift` both need the same two steps — export the
 * backend document, then run openapi-typescript over it — so that logic lives here
 * instead of being duplicated.
 */
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));

/** The `frontend/` directory. */
export const FRONTEND_DIR = path.resolve(SCRIPT_DIR, "..");

/** The repository root. */
export const REPO_ROOT = path.resolve(FRONTEND_DIR, "..");

/** The committed generated artifact. */
export const GENERATED_PATH = path.join(FRONTEND_DIR, "src", "api", "generated.ts");

const EXPORT_SCRIPT = path.join(SCRIPT_DIR, "export-openapi.py");
const OPENAPI_TYPESCRIPT_CLI = path.join(
  FRONTEND_DIR,
  "node_modules",
  "openapi-typescript",
  "bin",
  "cli.js",
);

/** The backend runtime, matching the interpreter the repository's scripts already use. */
function pythonCommand() {
  return process.platform === "win32"
    ? { command: "py", args: ["-3.14"] }
    : { command: "python3", args: [] };
}

/** Exports the current backend OpenAPI document to `outputPath`. */
export function exportOpenApiDocument(outputPath) {
  const { command, args } = pythonCommand();
  const result = spawnSync(command, [...args, EXPORT_SCRIPT, outputPath], {
    cwd: REPO_ROOT,
    encoding: "utf8",
  });
  if (result.status !== 0) {
    throw new Error(
      `backend OpenAPI export failed (${command} exit ${String(result.status)})\n` +
        `${result.stdout ?? ""}${result.stderr ?? ""}`,
    );
  }
}

/** Runs the committed openapi-typescript over `sourcePath`, writing `outputPath`. */
export function generateTypes(sourcePath, outputPath) {
  const result = spawnSync(process.execPath, [OPENAPI_TYPESCRIPT_CLI, sourcePath, "-o", outputPath], {
    cwd: FRONTEND_DIR,
    encoding: "utf8",
  });
  if (result.status !== 0) {
    throw new Error(
      `openapi-typescript failed (exit ${String(result.status)})\n` +
        `${result.stdout ?? ""}${result.stderr ?? ""}`,
    );
  }
}

/** Normalises line endings so drift comparison is about content, not checkout flavour. */
export function normalizeLineEndings(text) {
  return text.replace(/\r\n/g, "\n");
}
