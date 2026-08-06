from __future__ import annotations

import hashlib
import json
from pathlib import Path

import aiosqlite


def _hash(detail: dict) -> str:
    return hashlib.sha256(json.dumps(detail, sort_keys=True).encode()).hexdigest()[:16]


class StateStore:
    def __init__(self, path: Path):
        self.path = path

    async def init(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""CREATE TABLE IF NOT EXISTS runs (
              id TEXT PRIMARY KEY,
              repo TEXT NOT NULL, pr TEXT NOT NULL, rev TEXT NOT NULL,
              verdict TEXT NOT NULL,
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")
            await db.execute("""CREATE TABLE IF NOT EXISTS proposals (
              id TEXT PRIMARY KEY,
              run_id TEXT NOT NULL,
              kind TEXT NOT NULL, target_urn TEXT NOT NULL,
              detail_hash TEXT NOT NULL, detail TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'PROPOSED',
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")
            await db.execute("""CREATE UNIQUE INDEX IF NOT EXISTS idx_proposals_uniq
              ON proposals(kind, target_urn, detail_hash)""")
            await db.commit()

    async def record_run(self, run_id: str, repo: str, pr: str, rev: str, verdict: str) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO runs (id, repo, pr, rev, verdict) VALUES (?, ?, ?, ?, ?)",
                (run_id, repo, pr, rev, verdict),
            )
            await db.commit()

    async def proposal_exists(self, kind: str, target_urn: str, detail: dict) -> bool:
        async with aiosqlite.connect(self.path) as db:
            async with db.execute(
                "SELECT 1 FROM proposals WHERE kind=? AND target_urn=? AND detail_hash=?",
                (kind, target_urn, _hash(detail)),
            ) as cur:
                row = await cur.fetchone()
        return row is not None

    async def add_proposal(self, run_id: str, kind: str, target_urn: str, detail: dict) -> str:
        if await self.proposal_exists(kind, target_urn, detail):
            return ""
        proposal_id = f"{run_id}:{kind}:{target_urn}:{_hash(detail)}"
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO proposals (id, run_id, kind, target_urn, detail_hash, detail) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (proposal_id, run_id, kind, target_urn, _hash(detail), json.dumps(detail, sort_keys=True)),
            )
            await db.commit()
        return proposal_id

    async def set_status(self, proposal_id: str, status: str) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE proposals SET status=? WHERE id=?", (status, proposal_id))
            await db.commit()

    async def list_proposals(self, status: str | None = None) -> list[dict]:
        query = "SELECT kind, target_urn, detail, status, run_id FROM proposals"
        params: tuple = ()
        if status is not None:
            query += " WHERE status=?"
            params = (status,)
        query += " ORDER BY created_at DESC"
        async with aiosqlite.connect(self.path) as db:
            async with db.execute(query, params) as cur:
                rows = await cur.fetchall()
        return [
            {"kind": r[0], "target_urn": r[1], "detail": json.loads(r[2]), "status": r[3], "run_id": r[4]}
            for r in rows
        ]