# ML-first severity model

Severity is computed deterministically from DataHub lineage, in this order:

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