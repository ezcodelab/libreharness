// SPDX-License-Identifier: MIT
import { resolvePython } from "../src/runtime.js";

export const python = resolvePython();

export function pythonArgs(...args) {
  return [...python.prefixArgs, ...args];
}
