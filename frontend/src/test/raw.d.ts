/**
 * Ambient declaration for Vite's `?raw` imports, used by the generated-artifact test
 * to assert on the committed OpenAPI output as bytes rather than as types.
 */
declare module "*?raw" {
  const content: string;
  export default content;
}
