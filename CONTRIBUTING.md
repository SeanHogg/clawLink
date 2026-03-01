# Contributing to CoderClawLink

## Quick Links

- **GitHub:** https://github.com/seanhogg/coderclawlink
- **Discord:** https://discord.gg/qkhbAGHRBT
- **X/Twitter:** [@coderclaw](https://x.com/coderclaw)

---

## Project Structure

CoderClawLink is a pnpm workspace with two Cloudflare Worker packages:

```
coderclawlink/
├── api/        # api.coderclaw.ai — Hono REST API + Durable Objects + Postgres
└── app/        # app.coderclaw.ai — Vite + Lit SPA + static asset Worker
```

### `api/` — Backend

Four-layer DDD architecture: **Domain → Application → Infrastructure ← Presentation**

| Layer | Path | Description |
|-------|------|-------------|
| Domain | `src/domain/` | Pure business logic — entities, aggregates, port interfaces |
| Application | `src/application/` | Use-case services — depend on domain ports, not concretions |
| Infrastructure | `src/infrastructure/` | Drizzle/Postgres repos, JWT/Hash services, Durable Objects |
| Presentation | `src/presentation/` | Hono routes + middleware |

### `app/` — Frontend

Lit 3 web components built with Vite.

| Path | Description |
|------|-------------|
| `src/app.ts` | Root `<ccl-app>` — auth state machine + routing |
| `src/api.ts` | Typed fetch wrapper — manages JWT, dispatches `ccl:unauthorized` |
| `src/gateway.ts` | `ClawGateway` — WebSocket client for the claw relay |
| `src/views/` | Management views (projects, tasks, claws, skills, workspace, logs) |
| `src/views/claw/` | Claw panel views (chat, agents, config, sessions, etc.) |
| `src/styles.css` | Design system — CSS custom properties, no utility framework |

---

## Development Setup

### Prerequisites

- Node.js 20+, pnpm 9+
- [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/install-and-update/) authenticated (`wrangler login`)
- Postgres database (Neon, Supabase, etc.) accessible from the internet

### Install

```sh
pnpm install
```

### Local development

Three processes — run each in a separate terminal:

```sh
# 1. API Worker (http://localhost:8787)
pnpm dev:api

# 2. App Worker / static asset server (http://localhost:8788)
pnpm dev:app

# 3. Vite dev server for the UI (http://localhost:5173, proxies /api → 8787)
pnpm --filter app dev:ui
```

> For most UI work you only need terminals 1 and 3.
> `dev:ui` hot-reloads on save; `dev:app` serves the built `static/` output.

### Build the UI

```sh
pnpm --filter app build
# outputs to app/static/ — committed and served by the app Worker
```

### Type-check everything

```sh
pnpm --filter app type-check    # checks both tsconfig.json and tsconfig.ui.json
pnpm --filter api exec tsc --noEmit
```

### Database migrations

Migrations are tracked in a `_migrations` table and run automatically on `pnpm deploy`.
To run them manually:

```sh
# Get the connection string from Neon
npx neonctl connection-string --project-id <project-id> --org-id <org-id>

# Apply any pending migrations
DATABASE_URL=<connection-string> pnpm db:migrate

# Or store it in api/.env (never committed) and just run:
pnpm db:migrate
```

The project uses Neon org `org-shiny-mountain-55999992`, project `empty-smoke-28326171`.

```sh
# One-liner to get the connection string for this project:
npx neonctl connection-string --project-id empty-smoke-28326171 --org-id org-shiny-mountain-55999992
```

---

## Releasing / Deploying

Versions follow the **`YYYY.M.D`** scheme (e.g. `2026.2.27`). Always bump before deploying.

### Steps

1. **Bump version** in all three `package.json` files (root, `api/`, `app/`) to today's date:

   ```sh
   # root package.json
   # api/package.json
   # app/package.json
   # — set "version": "YYYY.M.D" in all three
   ```

2. **Ensure `api/.env` has `DATABASE_URL`** (needed by the migration runner):

   ```sh
   # Get it from Neon:
   npx neonctl connection-string --project-id empty-smoke-28326171 --org-id org-shiny-mountain-55999992
   # Then write to api/.env:
   # DATABASE_URL=postgresql://...
   ```

3. **Deploy both workers** (migrations run automatically before `wrangler deploy`):

   ```sh
   pnpm --filter api run deploy    # runs migrations then wrangler deploy
   pnpm --filter app run deploy    # vite build && wrangler deploy
   ```

   > Use `pnpm --filter <pkg> run deploy` (not `pnpm --filter <pkg> deploy`) — pnpm has its
   > own `deploy` command that conflicts with the npm script name.

### Checklist before deploying

- [ ] Version bumped in root, `api/`, and `app/` `package.json`
- [ ] `pnpm --filter app build` succeeds with no errors
- [ ] `api/.env` has a valid `DATABASE_URL` (migrations run automatically on deploy)
- [ ] Wrangler authenticated (`wrangler whoami`)

---

## How to Contribute

1. **Bugs & small fixes** → Open a PR directly.
2. **New features / architecture** → Open a [GitHub Discussion](https://github.com/seanhogg/coderclawlink/discussions) or ask in Discord first.
3. **Questions** → Discord `#setup-help`.

---

## Before You PR

- Test locally against a real CoderClaw instance if your change touches the relay or claw panel.
- Run `pnpm --filter app build` — the PR should not break the Vite build.
- Keep PRs focused: one concern per PR, no unrelated cleanups mixed in.
- Describe **what** changed and **why**.

---

## Lit Decorator Style

The UI uses Lit with **legacy** decorators. Keep the existing style for reactive fields:

```ts
@state() private items: Project[] = [];
@property() clawId = "";
@property({ type: Number }) count = 0;
```

Both `tsconfig.ui.json` files are configured with `experimentalDecorators: true` and
`useDefineForClassFields: false`. Do not change these without also updating the build tooling.

---

## AI/Vibe-Coded PRs Welcome!

Built with Claude, Codex, or another AI tool? Great — just mark it:

- [ ] AI-assisted label in the PR title or description
- [ ] Note the degree of testing (untested / lightly tested / fully tested)
- [ ] Include prompts or session logs if possible
- [ ] Confirm you understand what the code does

AI PRs are first-class here. We just want transparency so reviewers know what to look for.

---

## Report a Vulnerability

Report security issues directly via GitHub:

- **CoderClawLink API / relay** — [seanhogg/coderclawlink](https://github.com/seanhogg/coderclawlink)
- **CoderClaw core** — [seanhogg/coderclaw](https://github.com/seanhogg/coderclaw)

For issues that don't fit a specific repo, email **security@coderclaw.ai**.

### Required in Reports

1. Title
2. Severity assessment
3. Impact
4. Affected component
5. Technical reproduction steps
6. Demonstrated impact
7. Environment
8. Remediation advice

Reports without reproduction steps and demonstrated impact will be deprioritized.
