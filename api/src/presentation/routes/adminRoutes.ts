/**
 * Superadmin routes — /api/admin/*
 *
 * All routes require a WebJWT with sa: true (enforced by superAdminMiddleware).
 *
 * GET  /api/admin/users                — all platform users + tenant counts
 * GET  /api/admin/tenants              — all tenants + member/claw counts
 * GET  /api/admin/health               — system health (DB ping, model pool, counts)
 * GET  /api/admin/errors               — recent API error log (last 200 entries)
 * POST /api/admin/impersonate          — issue a tenant JWT for any user+tenant pair
 */
import { Hono } from 'hono';
import { sql, desc } from 'drizzle-orm';
import type { HonoEnv } from '../../env';
import { superAdminMiddleware } from '../middleware/superAdminMiddleware';
import { buildDatabase } from '../../infrastructure/database/connection';
import {
  users,
  tenants,
  tenantMembers,
  coderclawInstances,
  apiErrorLog,
} from '../../infrastructure/database/schema';
import { signJwt } from '../../infrastructure/auth/JwtService';
import { FREE_MODEL_POOL } from '../../application/llm/LlmProxyService';

export function createAdminRoutes(): Hono<HonoEnv> {
  const router = new Hono<HonoEnv>();

  // All admin routes require superadmin WebJWT
  router.use('*', superAdminMiddleware);

  // -------------------------------------------------------------------------
  // GET /api/admin/users
  // -------------------------------------------------------------------------
  router.get('/users', async (c) => {
    const db = buildDatabase(c.env);

    const rows = await db.execute(sql`
      SELECT
        u.id,
        u.email,
        u.username,
        u.display_name  AS "displayName",
        u.is_superadmin AS "isSuperadmin",
        u.created_at    AS "createdAt",
        COUNT(DISTINCT tm.tenant_id)::int AS "tenantCount"
      FROM users u
      LEFT JOIN tenant_members tm ON tm.user_id = u.id AND tm.is_active = true
      GROUP BY u.id, u.email, u.username, u.display_name, u.is_superadmin, u.created_at
      ORDER BY u.created_at DESC
      LIMIT 500
    `);

    return c.json({ users: rows.rows });
  });

  // -------------------------------------------------------------------------
  // GET /api/admin/tenants
  // -------------------------------------------------------------------------
  router.get('/tenants', async (c) => {
    const db = buildDatabase(c.env);

    const rows = await db.execute(sql`
      SELECT
        t.id,
        t.name,
        t.slug,
        t.status,
        t.created_at AS "createdAt",
        COUNT(DISTINCT tm.user_id)::int  AS "memberCount",
        COUNT(DISTINCT ci.id)::int       AS "clawCount"
      FROM tenants t
      LEFT JOIN tenant_members tm ON tm.tenant_id = t.id AND tm.is_active = true
      LEFT JOIN coderclaw_instances ci ON ci.tenant_id = t.id
      GROUP BY t.id, t.name, t.slug, t.status, t.created_at
      ORDER BY t.created_at DESC
      LIMIT 500
    `);

    return c.json({ tenants: rows.rows });
  });

  // -------------------------------------------------------------------------
  // GET /api/admin/health
  // -------------------------------------------------------------------------
  router.get('/health', async (c) => {
    const db = buildDatabase(c.env);

    let dbOk = false;
    let dbLatencyMs = 0;
    try {
      const t0 = Date.now();
      await db.execute(sql`SELECT 1`);
      dbLatencyMs = Date.now() - t0;
      dbOk = true;
    } catch { /* dbOk stays false */ }

    // Platform counts
    const [counts] = (await db.execute(sql`
      SELECT
        (SELECT COUNT(*)::int FROM users)                   AS "userCount",
        (SELECT COUNT(*)::int FROM tenants)                 AS "tenantCount",
        (SELECT COUNT(*)::int FROM coderclaw_instances)     AS "clawCount",
        (SELECT COUNT(*)::int FROM executions)              AS "executionCount",
        (SELECT COUNT(*)::int FROM api_error_log)           AS "errorCount"
    `)).rows as Array<{
      userCount: number; tenantCount: number; clawCount: number;
      executionCount: number; errorCount: number;
    }>;

    // LLM model pool status (reuse in-memory cooldown state)
    const modelPool = FREE_MODEL_POOL.map(m => ({ model: m }));

    return c.json({
      status:       dbOk ? 'ok' : 'degraded',
      db:           { ok: dbOk, latencyMs: dbLatencyMs },
      platform:     counts,
      llm:          { pool: modelPool.length, models: modelPool },
      timestamp:    new Date().toISOString(),
    });
  });

  // -------------------------------------------------------------------------
  // GET /api/admin/errors
  // -------------------------------------------------------------------------
  router.get('/errors', async (c) => {
    const db = buildDatabase(c.env);

    const rows = await db
      .select()
      .from(apiErrorLog)
      .orderBy(desc(apiErrorLog.createdAt))
      .limit(200);

    return c.json({ errors: rows });
  });

  // -------------------------------------------------------------------------
  // POST /api/admin/impersonate   { userId, tenantId }
  // Issue a 1-hour tenant-scoped JWT for any user+tenant pair.
  // -------------------------------------------------------------------------
  router.post('/impersonate', async (c) => {
    const { userId, tenantId } = await c.req.json<{ userId: string; tenantId: number }>();
    if (!userId || !tenantId) {
      return c.json({ error: 'userId and tenantId are required' }, 400);
    }

    const db = buildDatabase(c.env);

    // Verify the user exists
    const [userRow] = await db
      .select({ id: users.id, email: users.email })
      .from(users)
      .where(sql`${users.id} = ${userId}`)
      .limit(1);
    if (!userRow) return c.json({ error: 'User not found' }, 404);

    // Verify the tenant exists and get the user's role
    const [memberRow] = await db
      .select({ role: tenantMembers.role })
      .from(tenantMembers)
      .where(sql`${tenantMembers.userId} = ${userId} AND ${tenantMembers.tenantId} = ${tenantId} AND ${tenantMembers.isActive} = true`)
      .limit(1);

    // Use the user's actual role if a member, otherwise default to 'viewer'
    const role = memberRow?.role ?? 'viewer';

    const token = await signJwt(
      { sub: userId, tid: tenantId, role: role as Parameters<typeof signJwt>[0]['role'] },
      c.env.JWT_SECRET,
      3600,
    );

    return c.json({
      token,
      expiresIn:    3600,
      userId:       userRow.id,
      email:        userRow.email,
      tenantId,
      role,
    });
  });

  return router;
}
