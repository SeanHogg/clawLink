#!/usr/bin/env node
/**
 * Lightweight migration runner for Neon (HTTP transport).
 *
 * - Reads DATABASE_URL from api/.env or the environment.
 * - Tracks applied migrations in a _migrations table.
 * - Runs all *.sql files in migrations/ that haven't been applied yet.
 * - Called automatically by `pnpm deploy` before wrangler deploy.
 */

import { readFileSync, readdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { neon } from '@neondatabase/serverless';

const here = dirname(fileURLToPath(import.meta.url));

// ---------------------------------------------------------------------------
// Load .env (DATABASE_URL is a secret, never committed to source control)
// ---------------------------------------------------------------------------

function loadDotEnv(path) {
  try {
    const text = readFileSync(path, 'utf8');
    for (const line of text.split('\n')) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith('#')) continue;
      const eq = trimmed.indexOf('=');
      if (eq === -1) continue;
      const key = trimmed.slice(0, eq).trim();
      const val = trimmed.slice(eq + 1).trim().replace(/^["']|["']$/g, '');
      if (key && !process.env[key]) process.env[key] = val;
    }
  } catch { /* file not found – that's fine */ }
}

loadDotEnv(join(here, '../.env'));

const DATABASE_URL = process.env.DATABASE_URL;
if (!DATABASE_URL) {
  console.error('❌  DATABASE_URL not set.');
  console.error('   Create api/.env with: DATABASE_URL=postgresql://...');
  process.exit(1);
}

// ---------------------------------------------------------------------------
// Connect
// ---------------------------------------------------------------------------

const sql = neon(DATABASE_URL);

// ---------------------------------------------------------------------------
// Migration tracking table
// ---------------------------------------------------------------------------

await sql(`
  CREATE TABLE IF NOT EXISTS _migrations (
    name       TEXT        PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
  )
`);

const applied = new Set(
  (await sql('SELECT name FROM _migrations')).map(r => r.name),
);

// ---------------------------------------------------------------------------
// Discover & apply pending migrations
// ---------------------------------------------------------------------------

const migrationsDir = join(here, '../migrations');

let files;
try {
  files = readdirSync(migrationsDir)
    .filter(f => f.endsWith('.sql'))
    .sort();                     // apply in lexicographic order (0001_, 0002_, …)
} catch {
  console.log('ℹ️  No migrations/ directory – nothing to do.');
  process.exit(0);
}

let applied_count = 0;

for (const file of files) {
  if (applied.has(file)) continue;

  console.log(`  ⏳ Applying ${file}…`);

  const sqlText = readFileSync(join(migrationsDir, file), 'utf8');

  // Split on ';' and run each non-empty statement individually
  const stmts = sqlText
    .split(';')
    .map(s => s.replace(/--[^\n]*/g, '').trim())  // strip line comments
    .filter(Boolean);

  for (const stmt of stmts) {
    await sql(stmt);
  }

  await sql('INSERT INTO _migrations (name) VALUES ($1)', [file]);
  applied_count++;
  console.log(`  ✅ ${file}`);
}

if (applied_count === 0) {
  console.log('✅  Database is up to date.');
} else {
  console.log(`\n✅  Applied ${applied_count} migration(s).`);
}
