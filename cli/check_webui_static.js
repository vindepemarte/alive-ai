#!/usr/bin/env node
const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const htmlPath = path.join(root, "webui", "static", "index.html");
const manifestPath = path.join(root, "webui", "static", "manifest.json");

const html = fs.readFileSync(htmlPath, "utf8");
const scriptRegex = /<script\b[^>]*>([\s\S]*?)<\/script>/gi;
let count = 0;
for (const match of html.matchAll(scriptRegex)) {
  count += 1;
  try {
    new Function(match[1]);
  } catch (error) {
    console.error(`Invalid inline script #${count} in ${path.relative(root, htmlPath)}:`);
    console.error(error.message);
    process.exit(1);
  }
}

if (count === 0) {
  console.error(`No inline scripts found in ${path.relative(root, htmlPath)}`);
  process.exit(1);
}

JSON.parse(fs.readFileSync(manifestPath, "utf8"));
console.log(`WebUI static check passed (${count} inline script parsed).`);
