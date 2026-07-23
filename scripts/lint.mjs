import { readFile, readdir } from "node:fs/promises";
import { extname, resolve } from "node:path";

const extensions = new Set([".html", ".css", ".js", ".mjs", ".json", ".yml"]);
const ignoredDirectories = new Set([".git", "dist", "node_modules"]);
const issues = [];

async function collectFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = [];

  for (const entry of entries) {
    if (entry.isDirectory() && ignoredDirectories.has(entry.name)) {
      continue;
    }

    const path = resolve(directory, entry.name);
    if (entry.isDirectory()) {
      files.push(...(await collectFiles(path)));
    } else if (extensions.has(extname(entry.name))) {
      files.push(path);
    }
  }

  return files;
}

for (const file of await collectFiles(resolve("."))) {
  const content = await readFile(file, "utf8");
  const lines = content.split("\n");

  lines.forEach((line, index) => {
    if (/[ \t]+$/.test(line)) {
      issues.push(`${file}:${index + 1} contiene espacios al final`);
    }
    if (line.includes("\t")) {
      issues.push(`${file}:${index + 1} contiene una tabulación`);
    }
  });

  if (!content.endsWith("\n")) {
    issues.push(`${file} debe terminar con una línea nueva`);
  }
}

if (issues.length > 0) {
  console.error(issues.join("\n"));
  process.exitCode = 1;
} else {
  console.log("Lint completado sin errores.");
}

