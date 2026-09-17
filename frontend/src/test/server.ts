import { setupServer } from "msw/node";

import { handlers } from "./handlers";

/** The MSW server used by every frontend test. Lifecycle is owned by `setup.ts`. */
export const server = setupServer(...handlers);
