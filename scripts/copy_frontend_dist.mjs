import { cpSync, existsSync, mkdirSync, rmSync } from "node:fs";
import { resolve } from "node:path";

const source = resolve("frontend", "dist");
const target = resolve("dist");

if (!existsSync(source)) {
  throw new Error(`Frontend build output does not exist: ${source}`);
}

rmSync(target, { force: true, recursive: true });
mkdirSync(target, { recursive: true });
cpSync(source, target, { recursive: true });
