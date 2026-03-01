import { MiddlewareHandler } from 'hono';
import type { HonoEnv } from '../../env';
import { verifyWebJwt } from '../../infrastructure/auth/JwtService';
import { UnauthorizedError, ForbiddenError } from '../../domain/shared/errors';

/**
 * Middleware that gates access to superadmin-only endpoints.
 *
 * Expects a WebJWT (24-hour session token) with `sa: true` claim.
 * Sets `userId` in the Hono context for downstream use.
 */
export const superAdminMiddleware: MiddlewareHandler<HonoEnv> = async (c, next) => {
  const authHeader = c.req.header('Authorization') ?? '';
  if (!authHeader.startsWith('Bearer ')) {
    throw new UnauthorizedError('Missing or malformed Authorization header');
  }

  const token = authHeader.slice(7);
  let payload;
  try {
    payload = await verifyWebJwt(token, c.env.JWT_SECRET);
  } catch {
    throw new UnauthorizedError('Invalid or expired token');
  }

  if (!payload.sa) {
    throw new ForbiddenError('Superadmin access required');
  }

  c.set('userId', payload.sub);
  await next();
};
