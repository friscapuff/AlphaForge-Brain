// Simple bundler: reads canonical OpenAPI YAML and writes JSON output.
// Keeps logic minimal & deterministic. Future: add dereferencing if needed.

const fs = require('fs');
const yaml = require('yaml');

const INPUT = 'specs/001-initial-dual-tier/contracts/openapi.yaml';
const OUTPUT = 'openapi.json';

try {
  const text = fs.readFileSync(INPUT, 'utf8');
  const doc = yaml.parse(text);
  fs.writeFileSync(OUTPUT, JSON.stringify(doc, null, 2));
  console.log(`Bundled ${INPUT} -> ${OUTPUT}`);
} catch (err) {
  console.error('Bundle failed:', err);
  process.exit(1);
}
