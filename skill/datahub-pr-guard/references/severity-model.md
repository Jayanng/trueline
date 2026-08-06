# ML-first severity model

Severity is computed deterministically from DataHub lineage, in this order. It
describes blast radius and is retained independently from the contract decision.

| Severity | Rule | Example |
|---|---|---|
| CRITICAL | Non-additive change (DROP / TYPE_CHANGE) with any ML entity downstream (`urn:li:mlModel:*`, `urn:li:mlFeature:*`, `urn:li:mlFeatureTable:*`, `urn:li:mlPrimaryKey:*`, `urn:li:mlModelGroup:*`, `urn:li:mlModelDeployment:*`) | Dropping `return_date` hits `feature_order_risk` → `fraud_model_v4` [PROD] → `fraud-scoring-endpoint` |
| LOW (ML path) | Additive-only columns even if ML entities are downstream — no silent breakage | Adding `notes` with ML consumers listed for awareness |
| HIGH | Downstream dashboard/BI consumers (platforms: looker, tableau, powerbi, superset) | Change hits a Looker explore |
| MEDIUM | Multiple downstream datasets, or any non-additive change with no stronger signal | Column type change with one downstream table |
| LOW | Additive changes only (new columns), no downstream ML/dashboards | Adding a new column |

Owners are read from the ownership aspect; environment (PROD) from the entity's
custom properties / instance. Never invent either. Every CRITICAL verdict must cite
the lineage path it was computed from.

## Contract decisions

| Decision | Rule |
|---|---|
| ALLOW | Evidence is sufficient and no matching protected-input policy is violated. Additive-only changes remain `LOW` / `ALLOW`, including when ML entities are downstream. |
| BLOCK | A contracted critical input has a prohibited non-additive change and lineage verifies both the contract's model URN and deployment URN. |
| QUARANTINE | Expected contracted model or deployment evidence is absent, or catalog warnings such as `NO_DOWNSTREAM` / `NO_ML_LINEAGE` make the protected input unverified. Name each missing URN or warning and tell the operator to restore/seed the evidence and rerun. |
| REVIEW | A non-additive changed column has downstream lineage but no matching protected input. Keep the generic severity; `REVIEW` does not reduce it. |

Severity and decision answer different questions. A generic non-contract ML impact can
therefore be `CRITICAL` / `REVIEW`; a verified additive contract change is `LOW` /
`ALLOW`. Empty lineage is never safe evidence: a protected input with missing expected
evidence is `QUARANTINE`, not `ALLOW`.
