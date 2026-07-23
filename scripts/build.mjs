import { cp, mkdir, rm, stat } from "node:fs/promises";
import { resolve } from "node:path";

const sourceDirectory = resolve("src");
const outputDirectory = resolve("dist");

await rm(outputDirectory, { recursive: true, force: true });
await mkdir(outputDirectory, { recursive: true });
await cp(sourceDirectory, outputDirectory, { recursive: true });

for (const requiredFile of ["index.html", "styles.css", "app.js"]) {
  const file = await stat(resolve(outputDirectory, requiredFile));
  if (!file.isFile() || file.size === 0) {
    throw new Error(`El build no generó correctamente ${requiredFile}`);
  }
}

console.log("Build generado en dist/");

