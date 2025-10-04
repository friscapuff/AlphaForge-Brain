#!/usr/bin/env node
/**
 * Lightweight OpenAPI diff reporter (structural) without external openapi-diff dependency.
 * Strategy:
 * 1. Bundle & dereference both base and head via swagger-cli to JSON.
 * 2. Parse JSON and compare keys for: paths, components.schemas, components.parameters.
 * 3. Produce a categorized Markdown report (added / removed / changed operations & schemas).
 * 4. Changed detection = present in both but JSON.stringify differs (shallow for operations, full for schema).
 */
const { execSync } = require('child_process');
const fs = require('fs');

const SPEC_PATH = 'specs/001-initial-dual-tier/contracts/openapi.yaml';
const BASE_REF = process.env.BASE_REF || 'origin/main';

function run(cmd) {
  return execSync(cmd, { stdio: 'pipe', encoding: 'utf-8' });
}

function ensureBase() {
  try {
    run(`git fetch --depth=1 ${BASE_REF.split('/')[0]} ${BASE_REF.split('/')[1] || ''}`);
  } catch (e) {
    // ignore
  }
}

function getTempFile(prefix) {
  const p = `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2)}.json`;
  return p;
}

function bundle(ref, outFile) {
  const showCmd = `git show ${ref}:${SPEC_PATH}`;
  let yaml;
  try {
    yaml = run(showCmd);
  } catch (e) {
    return false; // spec might not exist on base
  }
  // sanitize tabs -> two spaces (historical older spec revisions may contain tabs)
  const sanitized = yaml.replace(/\t/g, '  ');
  fs.writeFileSync(outFile.replace(/\.json$/, '.yaml'), sanitized, 'utf-8');
  // deref & bundle to json stable form using swagger-cli
    try {
      run(`npx swagger-cli bundle ${outFile.replace(/\.json$/, '.yaml')} --outfile ${outFile} --type json`);
      return true;
    } catch (e) {
      console.warn(`Base spec bundling failed (${ref}); treating as empty. Reason: ${e.message}`);
      return false;
    }
}

function main() {
  ensureBase();
  const baseJson = getTempFile('base');
  const headJson = getTempFile('head');

  const baseOk = bundle(BASE_REF, baseJson);
  // current HEAD spec deref always
  run(`npx swagger-cli bundle ${SPEC_PATH} --outfile ${headJson} --type json`);

  if (!baseOk) {
    const headObjOnly = JSON.parse(fs.readFileSync(headJson,'utf-8'));
    const allPaths = Object.keys(headObjOnly.paths || {});
    const allSchemas = Object.keys(headObjOnly.components?.schemas || {});
    console.log(`# OpenAPI Diff (vs ${BASE_REF})\n\nBase spec unavailable or invalid; treating entire spec as added.\n\n### Paths Added (total ${allPaths.length})\n${allPaths.join(', ') || 'None'}\n\n### Schemas Added (total ${allSchemas.length})\n${allSchemas.join(', ') || 'None'}`);
    process.exit(0);
  }

  const baseObj = JSON.parse(fs.readFileSync(baseJson,'utf-8'));
  const headObj = JSON.parse(fs.readFileSync(headJson,'utf-8'));

  function diffKeys(baseSection, headSection) {
    const added = [];
    const removed = [];
    const changed = [];
    const baseKeys = new Set(Object.keys(baseSection || {}));
    const headKeys = new Set(Object.keys(headSection || {}));
    for (const k of headKeys) {
      if (!baseKeys.has(k)) added.push(k);
      else {
        const b = JSON.stringify(baseSection[k]);
        const h = JSON.stringify(headSection[k]);
        if (b !== h) changed.push(k);
      }
    }
    for (const k of baseKeys) {
      if (!headKeys.has(k)) removed.push(k);
    }
    return { added, removed, changed };
  }

  const pathDiff = diffKeys(baseObj.paths, headObj.paths);
  const schemaDiff = diffKeys(baseObj.components?.schemas, headObj.components?.schemas);

  function section(title, diff) {
    return `### ${title}\nAdded: ${diff.added.length ? diff.added.join(', ') : 'None'}\n\nRemoved: ${diff.removed.length ? diff.removed.join(', ') : 'None'}\n\nChanged: ${diff.changed.length ? diff.changed.join(', ') : 'None'}\n`;
  }

  console.log(`# OpenAPI Diff (vs ${BASE_REF})\n\n${section('Paths', pathDiff)}\n${section('Schemas', schemaDiff)}`);
  process.exit(0);
}

main();
