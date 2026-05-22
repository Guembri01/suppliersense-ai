# SupplierSense AI Frontend

React 18 + TypeScript + Tailwind + Recharts — DARK theme.

## Quick Start
```bash
cd frontend
npm install && npm run dev
```

## Type Check: `npx tsc --noEmit`

## Design System (Dark)
- Indigo/violet glassmorphism login (3 blobs)
- Dark SkeletonCard (`bg-gray-800/50 border-gray-700`)
- Dark ChartTooltip (`bg-gray-900`)
- Dark Toaster style
- Globe icon branding for global supply chain

## Build
```bash
npm run build
```
Output is placed in `dist/`. Use this before deploying to production.

## Structure
- `src/pages/` — Suppliers, SupplierDetail, Alerts, Geopolitical, Disruptions, Analytics
- `src/components/` — Layout, SkeletonCard
