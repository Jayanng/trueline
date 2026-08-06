# Task 5 Report

## Status

Implemented the synthetic clinical DataHub graph assets, gateway fake path, contract-aware verifier, SQL models, and table mappings. Live seeding and verification are blocked because the configured DataHub and MCP services are unreachable.

## RED Evidence

Command:

```text
python -m pytest tests/test_gateway_contract.py -q
```

Result before adding clinical graph facts: `1 failed, 7 passed`. The new test failed at the expected assertion because the downstream clinical model/deployment set was empty.

## GREEN Evidence

Required command:

```text
python -m pytest tests/test_gateway_contract.py tests/test_decision.py -q
```

Result: `15 passed, 1 warning in 1.32s`.

Full regression command:

```text
python -m pytest -q
```

Result: `86 passed, 2 skipped, 1 warning in 5.06s`. The warning is DataHub's experimental SDK warning.

Additional checks:

```text
python -m py_compile seed/seed_clinical_tail.py seed/verify_clinical_graph.py
git diff --check
```

Both completed successfully. Importing seed constants produced the exact required dataset, model, and deployment URNs.

## Live Evidence

Infrastructure probes:

```text
curl.exe --connect-timeout 3 --max-time 5 http://localhost:8080/health
curl.exe --connect-timeout 3 --max-time 5 http://127.0.0.1:8000/mcp
```

Both returned curl HTTP code `000`, meaning the TCP/HTTP services were unreachable. Per the task brief, `seed/seed_clinical_tail.py` and `seed/verify_clinical_graph.py` were not run against live infrastructure. No live metadata was written, and live verification is not claimed.

## Commit

Commit message: `feat: seed synthetic sepsis model lineage`.

Only Task 5 changes are staged. The pre-existing `FakeGateway.add_lineage` validation hunk and all other unrelated dirty files remain unstaged.

## Self-Review

- Confirmed contract URNs exactly match seeded constants.
- Confirmed fake lineage follows `patient_labs -> sepsis_features -> lactate_trend -> sepsis_risk_v3 -> icu-early-warning` within four hops.
- Confirmed owner and model/deployment environment assertions are explicit.
- Confirmed verifier checks contract input/model/deployment URNs, downstream entities, ownership, environments, and MCP search before printing `VERIFY CLINICAL OK`.
- Confirmed every seeded entity description and custom property labels it synthetic demo metadata.
- Confirmed the seed includes no patient records or real endpoint URL.
- Found a reversed positional argument issue in `make_ml_model_urn` during construction checks; corrected it to named arguments and reverified the exact URN.
- Preserved existing fraud facts and unrelated working-tree changes.

## Concerns

- Live DataHub aspect acceptance, lineage traversal, ownership projection, and MCP search remain unverified until DataHub GMS and MCP are reachable.
- The local test suite emits the existing experimental DataHub SDK warning.

## Review Round 1

Reviewer finding: verifier and gateway tests proved only independent entity membership, not the exact connected clinical path.

RED command:

```text
python -m pytest tests/test_verify_clinical_graph.py tests/test_gateway_contract.py -q
```

Result before the fix: `1 failed, 8 passed`. A gateway supplied all expected URNs, owner, environments, and search hits but reordered the feature/model nodes in the deployment path. The verifier incorrectly printed `VERIFY CLINICAL OK` and did not exit.

Fix:

- Added the pure `has_exact_clinical_deployment_path` predicate.
- The predicate scans `LineageResult.paths` across all downstream results and accepts only the exact contiguous tuple `patient_labs -> sepsis_features -> lactate_trend -> sepsis_risk_v3 -> icu-early-warning`.
- Updated the gateway contract test to assert that exact tuple on the fake deployment result.
- Added a verifier test proving mere URN membership with a broken intermediate path exits 1 and reports `FAIL: exact clinical deployment path is missing`.

GREEN commands:

```text
python -m pytest tests/test_verify_clinical_graph.py tests/test_gateway_contract.py -q
python -m pytest tests/test_gateway_contract.py tests/test_decision.py tests/test_verify_clinical_graph.py -q
python -m py_compile seed/verify_clinical_graph.py tests/test_verify_clinical_graph.py
```

Results: `9 passed`, then `16 passed`; compilation succeeded. Test runs retained only the existing experimental DataHub SDK warning.

Live probes were repeated against `http://localhost:8080/health` and `http://127.0.0.1:8000/mcp`; both again returned curl code `000`. Live seeding and verification remain blocked and are not claimed.
