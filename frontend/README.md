# VisionQuery frontend

Next.js 16 / React 19. See the [root README](../README.md) for backend setup and scan semantics.

```bash
npm ci
npm run dev
```

Open http://localhost:3000. Optional backend override: copy `.env.example` to `.env.local`, edit `NEXT_PUBLIC_BACKEND_URL`, and restart/rebuild.

Checks:

```bash
npm run lint
npm test
npm run typecheck
npm run build
```

Use Node.js 22.12+ or 20.19+. For laptop acceptance steps, see [RESEARCH_PREP.md](../docs/RESEARCH_PREP.md).
