# Trueline website (`web/`)

Five pages only — matches `DESIGN.md` §2 site map and the Python codebase.

| Route | Name | Reflects |
|---|---|---|
| `/` | Landing | Thesis, readout, three moments |
| `/guard` | The guard | `trueline/*`, `run_local.py`, severity, red/green PR |
| `/lineage` | ML lineage | seed, MCP/GMS/SDK, path to deployment |
| `/skill` | OSS skill | `skill/datahub-pr-guard/` |
| `/start` | Run it | Setup + CLI (no video embed; YouTube external) |

## Dev

```bash
cd web
npm install
npm run dev
```

Open http://localhost:3000

## Design

Black canvas · lime `#82C200` · mono · zero radius — see root `DESIGN.md`.
