/**
 * CoderClaw instance routes – /api/claws
 *
 * CoderClaw instances are registered machines owned by a tenant.
 * Each instance authenticates with its own API key (not a user credential).
 * One claw = one tenant. Users manage their mesh from the web UI.
 *
 * All routes require a tenant-scoped JWT (authMiddleware).
 */
import { Hono } from 'hono';
import { eq, and } from 'drizzle-orm';
import { authMiddleware } from '../middleware/authMiddleware';
import { coderclawInstances } from '../../infrastructure/database/schema';
import { generateApiKey, hashSecret } from '../../infrastructure/auth/HashService';
import type { HonoEnv } from '../../env';
import type { Db } from '../../infrastructure/database/connection';

export function createClawRoutes(db: Db): Hono<HonoEnv> {
  const router = new Hono<HonoEnv>();
  router.use('*', authMiddleware);

  // GET /api/claws – list all claws for the current tenant
  router.get('/', async (c) => {
    const tenantId = c.get('tenantId') as number;
    const rows = await db
      .select({
        id:           coderclawInstances.id,
        name:         coderclawInstances.name,
        slug:         coderclawInstances.slug,
        status:       coderclawInstances.status,
        registeredBy: coderclawInstances.registeredBy,
        lastSeenAt:   coderclawInstances.lastSeenAt,
        createdAt:    coderclawInstances.createdAt,
      })
      .from(coderclawInstances)
      .where(eq(coderclawInstances.tenantId, tenantId));
    return c.json({ claws: rows });
  });

  // POST /api/claws – register a new CoderClaw instance
  // Returns the plaintext API key once – it is never stored in plaintext.
  router.post('/', async (c) => {
    const tenantId = c.get('tenantId') as number;
    const userId   = c.get('userId') as string;
    const body     = await c.req.json<{ name: string }>();

    if (!body.name?.trim()) {
      return c.json({ error: 'name is required' }, 400);
    }

    const slug    = body.name.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-');
    const rawKey  = generateApiKey();
    const keyHash = await hashSecret(rawKey);

    const [inserted] = await db
      .insert(coderclawInstances)
      .values({
        tenantId,
        name:         body.name.trim(),
        slug,
        apiKeyHash:   keyHash,
        registeredBy: userId,
      })
      .returning({
        id:        coderclawInstances.id,
        name:      coderclawInstances.name,
        slug:      coderclawInstances.slug,
        status:    coderclawInstances.status,
        createdAt: coderclawInstances.createdAt,
      });

    return c.json({
      claw:   inserted,
      apiKey: rawKey,
      note:   'Save this API key — it will not be shown again. Paste it into your CoderClaw config.',
    }, 201);
  });

  // DELETE /api/claws/:id – deactivate / remove a claw
  router.delete('/:id', async (c) => {
    const tenantId = c.get('tenantId') as number;
    const id       = Number(c.req.param('id'));
    await db
      .delete(coderclawInstances)
      .where(and(eq(coderclawInstances.id, id), eq(coderclawInstances.tenantId, tenantId)));
    return c.body(null, 204);
  });

  return router;
}
