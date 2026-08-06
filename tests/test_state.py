import pytest

from trueline.state import StateStore


@pytest.mark.asyncio
async def test_proposal_idempotency(tmp_path):
    store = StateStore(tmp_path / "state.db")
    await store.init()
    detail = {"upstream": "u", "mapping": {"a": ["b"]}}
    first = await store.add_proposal("run-1", "LINEAGE", "urn:down", detail)
    second = await store.add_proposal("run-1", "LINEAGE", "urn:down", detail)
    assert first
    assert second == ""
    assert await store.proposal_exists("LINEAGE", "urn:down", detail)


@pytest.mark.asyncio
async def test_run_record_and_proposals(tmp_path):
    store = StateStore(tmp_path / "state.db")
    await store.init()
    await store.record_run("run-1", "trueline", "2847", "abc123", "CRITICAL")
    pid = await store.add_proposal("run-1", "GLOSSARY_TERM", "urn:x", {"column": "a", "term": "t"})
    await store.set_status(pid, "COMMITTED")
    committed = await store.list_proposals(status="COMMITTED")
    assert len(committed) == 1
    assert committed[0]["detail"]["column"] == "a"
    assert await store.proposal_exists("GLOSSARY_TERM", "urn:x", {"column": "a", "term": "t"})