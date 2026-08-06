"""Fail nonzero unless the synthetic clinical contract graph is live and complete."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

from trueline.config import Config, TableRef
from trueline.datahub_client import DataHubGateway

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
CONTRACTS_PATH = ROOT / "contracts" / "model-change-contracts.json"
PATIENT_LABS = TableRef("snowflake", "clinical", "", "patient_labs")
ML_FEATURE_URN = "urn:li:mlFeature:(clinical,lactate_trend)"
ML_MODEL_URN = "urn:li:mlModel:(urn:li:dataPlatform:mlflow,sepsis_risk_v3,PROD)"
ML_DEPLOY_URN = "urn:li:mlModelDeployment:(urn:li:dataPlatform:mlflow,icu-early-warning,PROD)"


def _search_contains(gateway: DataHubGateway, query: str, expected: str) -> bool:
    return expected in gateway.search(query=query, entity_type="", limit=20)


def main() -> None:
    failures: list[str] = []
    try:
        contracts = json.loads(CONTRACTS_PATH.read_text(encoding="utf-8")).get("contracts", [])
        contract = next((item for item in contracts if item.get("id") == "sepsis-risk-v3-prod"), None)
    except (OSError, json.JSONDecodeError) as exc:
        contract = None
        failures.append(f"cannot load contracts: {exc}")

    if contract is None:
        failures.append("missing expected contract: sepsis-risk-v3-prod")
    else:
        if contract.get("model_urn") != ML_MODEL_URN:
            failures.append(f"contract model URN does not match seeded URN: {contract.get('model_urn')!r}")
        if contract.get("deployment_urn") != ML_DEPLOY_URN:
            failures.append(
                f"contract deployment URN does not match seeded URN: {contract.get('deployment_urn')!r}"
            )
        input_urns = {item.get("dataset_urn") for item in contract.get("critical_inputs", [])}
        if PATIENT_LABS.urn not in input_urns:
            failures.append(f"contract missing expected input URN: {PATIENT_LABS.urn}")

    try:
        gateway = DataHubGateway(Config())
        results = gateway.downstream(PATIENT_LABS, max_hops=4)
        downstream_urns = {result.urn for result in results}
        for urn in (ML_FEATURE_URN, ML_MODEL_URN, ML_DEPLOY_URN):
            if urn not in downstream_urns:
                failures.append(f"missing downstream clinical entity: {urn}")

        owners = gateway.owners(ML_MODEL_URN)
        if "clinical-ml-oncall" not in owners:
            failures.append(f"model owner missing clinical-ml-oncall (got {owners})")
        for label, urn in (("model", ML_MODEL_URN), ("deployment", ML_DEPLOY_URN)):
            env = gateway.environment(urn)
            if env != "PROD":
                failures.append(f"{label} environment not PROD (got {env!r})")
        for query, urn in (("sepsis_risk_v3", ML_MODEL_URN), ("icu-early-warning", ML_DEPLOY_URN)):
            if not _search_contains(gateway, query, urn):
                failures.append(f"{query} not found via MCP search")
    except Exception as exc:
        failures.append(f"DataHub/MCP verification unavailable: {type(exc).__name__}: {exc}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        raise SystemExit(1)
    print("VERIFY CLINICAL OK")


if __name__ == "__main__":
    main()
