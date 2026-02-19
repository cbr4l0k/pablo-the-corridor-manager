/* eslint-disable */
/**
 * Generated `api` utility.
 *
 * THIS CODE IS AUTOMATICALLY GENERATED.
 *
 * To regenerate, run `npx convex dev`.
 * @module
 */

import type * as constants from "../constants.js";
import type * as jobs from "../jobs.js";
import type * as lib_time from "../lib/time.js";
import type * as lib_uniqueness from "../lib/uniqueness.js";
import type * as optouts from "../optouts.js";
import type * as people from "../people.js";
import type * as seedData from "../seedData.js";
import type * as seedStatus from "../seedStatus.js";
import type * as seeds from "../seeds.js";
import type * as status from "../status.js";
import type * as tasks from "../tasks.js";
import type * as weeks from "../weeks.js";

import type {
  ApiFromModules,
  FilterApi,
  FunctionReference,
} from "convex/server";

declare const fullApi: ApiFromModules<{
  constants: typeof constants;
  jobs: typeof jobs;
  "lib/time": typeof lib_time;
  "lib/uniqueness": typeof lib_uniqueness;
  optouts: typeof optouts;
  people: typeof people;
  seedData: typeof seedData;
  seedStatus: typeof seedStatus;
  seeds: typeof seeds;
  status: typeof status;
  tasks: typeof tasks;
  weeks: typeof weeks;
}>;

/**
 * A utility for referencing Convex functions in your app's public API.
 *
 * Usage:
 * ```js
 * const myFunctionReference = api.myModule.myFunction;
 * ```
 */
export declare const api: FilterApi<
  typeof fullApi,
  FunctionReference<any, "public">
>;

/**
 * A utility for referencing Convex functions in your app's internal API.
 *
 * Usage:
 * ```js
 * const myFunctionReference = internal.myModule.myFunction;
 * ```
 */
export declare const internal: FilterApi<
  typeof fullApi,
  FunctionReference<any, "internal">
>;

export declare const components: {};
