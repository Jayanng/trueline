from trueline.datahub_client import DataHubGateway, LineageResult

ROOT = "urn:li:dataset:(urn:li:dataPlatform:snowflake,clinical.patient_labs,PROD)"
FEATURES = "urn:li:dataset:(urn:li:dataPlatform:snowflake,clinical.sepsis_features,PROD)"
INTERMEDIATE = "urn:li:dataset:(urn:li:dataPlatform:snowflake,clinical.cleaned_labs,PROD)"
SIBLING = "urn:li:dataset:(urn:li:dataPlatform:snowflake,clinical.other_asset,PROD)"


def _results(*pairs):
    return [LineageResult(urn=urn, entity_type="dataset", platform="snowflake", name=urn, hops=hops)
            for urn, hops in pairs]


def test_chain_base_is_root():
    known = _results((ROOT, 0), (FEATURES, 1))
    assert DataHubGateway._dataset_chain(ROOT, ROOT, known) == (ROOT,)


def test_chain_single_hop_includes_root_and_base():
    known = _results((ROOT, 0), (FEATURES, 1))
    assert DataHubGateway._dataset_chain(ROOT, FEATURES, known) == (ROOT, FEATURES)


def test_chain_multi_hop_orders_by_distance():
    known = _results((ROOT, 0), (INTERMEDIATE, 1), (FEATURES, 2))
    assert DataHubGateway._dataset_chain(ROOT, FEATURES, known) == (ROOT, INTERMEDIATE, FEATURES)


def test_chain_excludes_same_hop_siblings():
    known = _results((ROOT, 0), (FEATURES, 1), (SIBLING, 1))
    assert DataHubGateway._dataset_chain(ROOT, FEATURES, known) == (ROOT, FEATURES)
