import postgres from 'postgres';
import { drizzle, PostgresJsDatabase } from 'drizzle-orm/postgres-js';
import * as schema from './schema';
import type { Env } from '../../env';

export type Db = PostgresJsDatabase<typeof schema>;

/**
 * Build a Drizzle database instance from the DATABASE_URL secret.
 *
 * Using `max: 1` is required inside a Cloudflare Worker because persistent
 * connections are not supported across requests.
 */
export function buildDatabase(env: Env): Db {
  const client = postgres(env.DATABASE_URL, {
    max: 1,
    prepare: false,
  });
  return drizzle(client, { schema });
}
