/**
 * coderClawLLM routes — OpenAI-compatible LLM proxy.
 *
 * POST  /v1/chat/completions   – proxied chat completion (429 failover)
 * GET   /v1/models             – list the free model pool + status
 * GET   /v1/health             – health check
 */
import { Hono } from 'hono';
import type { HonoEnv } from '../../env';
import {
  LlmProxyService,
  FREE_MODEL_POOL,
  type ChatCompletionRequest,
  type LlmUsage,
} from '../../application/llm/LlmProxyService';
import { buildDatabase } from '../../infrastructure/database/connection';
import { llmUsageLog, llmFailoverLog } from '../../infrastructure/database/schema';
import type { FailoverEvent } from '../../application/llm/LlmProxyService';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Bulk-insert failover events into llm_failover_log, fire-and-forget. */
function logFailovers(
  env: HonoEnv['Bindings'],
  ctx: ExecutionContext,
  failovers: FailoverEvent[],
): void {
  if (failovers.length === 0) return;
  ctx.waitUntil(
    buildDatabase(env)
      .insert(llmFailoverLog)
      .values(failovers.map(f => ({ model: f.model, errorCode: f.code })))
      .catch(() => { /* never let logging fail the request */ }),
  );
}

/** Write one row to llm_usage_log, fire-and-forget via ctx.waitUntil. */
function logUsage(
  env: HonoEnv['Bindings'],
  ctx: ExecutionContext,
  model: string,
  retries: number,
  streamed: boolean,
  usage: LlmUsage,
): void {
  ctx.waitUntil(
    buildDatabase(env)
      .insert(llmUsageLog)
      .values({
        model,
        promptTokens:     usage.promptTokens,
        completionTokens: usage.completionTokens,
        totalTokens:      usage.totalTokens,
        retries,
        streamed,
      })
      .catch(() => { /* never let logging fail the request */ }),
  );
}

/**
 * Wrap a ReadableStream to intercept OpenRouter SSE usage data from the final
 * chunk before [DONE], then call onUsage with the extracted counts.
 *
 * OpenRouter emits usage in the second-to-last data line:
 *   data: {...,"usage":{"prompt_tokens":N,"completion_tokens":M,"total_tokens":P}}
 *   data: [DONE]
 */
function wrapStreamForUsage(
  source: ReadableStream<Uint8Array>,
  onUsage: (usage: LlmUsage) => void,
): ReadableStream<Uint8Array> {
  const decoder = new TextDecoder();
  let lastDataJson = '';

  const { readable, writable } = new TransformStream<Uint8Array, Uint8Array>({
    transform(chunk, controller) {
      const text = decoder.decode(chunk, { stream: true });
      // Track the last non-[DONE] data line in this chunk
      for (const line of text.split('\n')) {
        const trimmed = line.trim();
        if (trimmed.startsWith('data: ') && trimmed !== 'data: [DONE]') {
          lastDataJson = trimmed.slice(6);
        } else if (trimmed === 'data: [DONE]' && lastDataJson) {
          try {
            const parsed = JSON.parse(lastDataJson) as Record<string, unknown>;
            const raw = parsed['usage'] as { prompt_tokens?: number; completion_tokens?: number; total_tokens?: number } | undefined;
            if (raw) {
              onUsage({
                promptTokens:     raw.prompt_tokens     ?? 0,
                completionTokens: raw.completion_tokens ?? 0,
                totalTokens:      raw.total_tokens      ?? 0,
              });
            }
          } catch { /* ignore parse errors */ }
        }
      }
      controller.enqueue(chunk);
    },
  });

  source.pipeTo(writable).catch(() => { /* stream may be cancelled by client */ });
  return readable;
}

// ---------------------------------------------------------------------------
// Routes
// ---------------------------------------------------------------------------

export function createLlmRoutes(): Hono<HonoEnv> {
  const router = new Hono<HonoEnv>();

  // -----------------------------------------------------------------------
  // POST /v1/chat/completions
  // -----------------------------------------------------------------------
  router.post('/v1/chat/completions', async (c) => {
    const apiKey = c.env.OPENROUTER_API_KEY;
    if (!apiKey) {
      return c.json({ error: 'LLM proxy not configured (missing OPENROUTER_API_KEY)' }, 503);
    }

    const body = await c.req.json<ChatCompletionRequest>();
    if (!body.messages || !Array.isArray(body.messages) || body.messages.length === 0) {
      return c.json({ error: 'messages array is required' }, 400);
    }

    const service = new LlmProxyService(apiKey);
    const result = await service.complete(body);

    // Clone upstream headers we care about
    const upstreamHeaders = new Headers();
    const contentType = result.response.headers.get('content-type');
    if (contentType) upstreamHeaders.set('content-type', contentType);
    upstreamHeaders.set('x-coderclaw-model', result.resolvedModel);
    upstreamHeaders.set('x-coderclaw-retries', String(result.retries));

    // ── Streaming ────────────────────────────────────────────────────────────
    if (body.stream && result.response.body) {
      upstreamHeaders.set('cache-control', 'no-cache');
      upstreamHeaders.set('connection', 'keep-alive');

      // Log any failovers that happened before this successful model
      logFailovers(c.env, c.executionCtx, result.failovers);

      // Wrap the stream to capture usage from the final SSE chunk
      const instrumentedStream = wrapStreamForUsage(
        result.response.body,
        (usage) => logUsage(c.env, c.executionCtx, result.resolvedModel, result.retries, true, usage),
      );

      return new Response(instrumentedStream, {
        status: result.response.status,
        headers: upstreamHeaders,
      });
    }

    // ── Non-streaming ────────────────────────────────────────────────────────
    const upstream = await result.response.json() as Record<string, unknown>;

    // Log any failovers, then log usage
    logFailovers(c.env, c.executionCtx, result.failovers);
    logUsage(
      c.env,
      c.executionCtx,
      result.resolvedModel,
      result.retries,
      false,
      result.usage ?? { promptTokens: 0, completionTokens: 0, totalTokens: 0 },
    );

    return c.json(
      {
        ...upstream,
        _coderclaw: {
          resolvedModel: result.resolvedModel,
          retries:       result.retries,
          pool:          FREE_MODEL_POOL.length,
        },
      },
      result.response.status as 200,
    );
  });

  // -----------------------------------------------------------------------
  // GET /v1/models — pool status
  // -----------------------------------------------------------------------
  router.get('/v1/models', async (c) => {
    const apiKey = c.env.OPENROUTER_API_KEY;
    if (!apiKey) {
      return c.json({ configured: false, models: FREE_MODEL_POOL });
    }
    const service = new LlmProxyService(apiKey);
    return c.json({
      configured: true,
      object: 'list',
      data: service.status(),
    });
  });

  // -----------------------------------------------------------------------
  // GET /v1/health
  // -----------------------------------------------------------------------
  router.get('/v1/health', (c) =>
    c.json({ status: 'ok', service: 'coderClawLLM', pool: FREE_MODEL_POOL.length }),
  );

  return router;
}
