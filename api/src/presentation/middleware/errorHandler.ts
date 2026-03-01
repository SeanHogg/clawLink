import { Context } from 'hono';
import {
  NotFoundError,
  ConflictError,
  ValidationError,
  ForbiddenError,
  UnauthorizedError,
} from '../../domain/shared/errors';
import { buildDatabase } from '../../infrastructure/database/connection';
import { apiErrorLog } from '../../infrastructure/database/schema';

/**
 * Global error handler for the Hono application.
 *
 * Maps domain errors to HTTP status codes and returns a consistent JSON body.
 * Unknown errors are logged to the DB (for admin visibility) and surfaced as 500s.
 */
export async function errorHandler(err: Error, c: Context): Promise<Response> {
  if (err instanceof ValidationError)  return c.json({ error: err.message }, 400);
  if (err instanceof UnauthorizedError) return c.json({ error: err.message }, 401);
  if (err instanceof ForbiddenError)   return c.json({ error: err.message }, 403);
  if (err instanceof NotFoundError)    return c.json({ error: err.message }, 404);
  if (err instanceof ConflictError)    return c.json({ error: err.message }, 409);

  // Unexpected errors — log to DB for admin visibility
  console.error('[unhandled]', err);
  const message = err instanceof Error ? err.message : String(err);
  const stack   = err instanceof Error ? (err.stack ?? null) : null;

  try {
    const env = c.env as { DATABASE_URL?: string };
    if (env.DATABASE_URL) {
      const db = buildDatabase(env as Parameters<typeof buildDatabase>[0]);
      await db.insert(apiErrorLog).values({
        method:  c.req.method,
        path:    new URL(c.req.url).pathname,
        message,
        stack,
      });
    }
  } catch { /* never let logging failures mask the real error response */ }

  return c.json({ error: message }, 500);
}
