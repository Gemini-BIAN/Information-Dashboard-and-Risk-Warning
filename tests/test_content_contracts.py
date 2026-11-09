"""Phase-one contract tests, not a production classifier accuracy benchmark."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from scm.content.contracts import (
    EVENT_KINDS,
    PRIORITIES,
    Applicability,
    IntelligenceRecord,
    SourceRegistry,
)

ROOT = Path(__file__).resolve().parents[1]


def record():
    return dict(
        record_id="synthetic-only",
        data_mode="fixture",
        source_id="test-source",
        source_name="Synthetic",
        source_type="official",
        organization_id="synthetic",
        canonical_url="https://example.org/synthetic",
        permitted_method="html_metadata",
        reuse_audit_ref="synthetic",
        original_title="合成测试",
        fetched_at="2026-11-09T00:00:00Z",
        last_verified_at="2026-11-09T00:00:00Z",
        severity_reasons=["未评估"],
        business_relevance={"reason_codes": ["UNKNOWN"], "reasons_zh": ["未核实"]},
        dedup_key="fixture:synthetic",
        update_version=1,
        quality_flags=["SYNTHETIC"],
    )


def test_catalog_and_taxonomy_are_versioned():
    catalog = SourceRegistry.model_validate_json((ROOT / "config/content_sources.v1.json").read_text())
    assert len(catalog.sources) == 23
    restricted = next(s for s in catalog.sources if s.source_id == "rotterdam")
    assert restricted.proposed_method == "link_only"
    assert restricted.reuse_permission == "prohibited"
    taxonomy = json.loads((ROOT / "config/content_taxonomy.v1.json").read_text())
    assert {d["code"]: d["event_kinds"] for d in taxonomy["domains"]} == EVENT_KINDS
    for name, model in [("intelligence", IntelligenceRecord), ("source_registry", SourceRegistry)]:
        assert (
            json.loads((ROOT / f"docs/schemas/{name}.v1.schema.json").read_text())
            == model.model_json_schema()
        )


@pytest.mark.parametrize("case", json.loads((ROOT / "fixtures/content_cases.v1.json").read_text()))
def test_synthetic_classification_labels_are_valid_contracts(case):
    data = record()
    data.update(
        primary_domain=case["domain"],
        event_kind=case["kind"],
        implementation_priority=PRIORITIES.get(case["domain"]),
        event_lifecycle=case.get("lifecycle", "unknown"),
    )
    data["business_relevance"]["decision"] = case["relevance"]
    parsed = IntelligenceRecord(**data)
    assert parsed.operational_state == "unknown"


@pytest.mark.parametrize(
    "patch",
    [
        {"fetched_at": "2026-11-09T00:00:00"},
        {"canonical_url": "https://example.org/?token=secret"},
        {"primary_domain": "A", "implementation_priority": "P2"},
        {"primary_domain": "A", "implementation_priority": "P0", "event_kind": "battery_regulation"},
        {"factual_summary_zh": [{"text_zh": "无证据事实", "evidence_ids": ["missing"]}]},
        {"operational_state": "confirmed_current_disruption"},
        {
            "primary_domain": "E",
            "implementation_priority": "P1",
            "business_relevance": {"decision": "relevant", "reason_codes": ["x"], "reasons_zh": ["x"]},
        },
    ],
)
def test_invalid_evidence_and_states_rejected(patch):
    with pytest.raises(ValidationError):
        IntelligenceRecord(**(record() | patch))


def test_dates_do_not_promote_legal_status_or_electrolyte_scope():
    legal = Applicability(effective_at="2020-01-01T00:00:00Z", applicability_note_zh="需要核实产品范围")
    assert legal.status == "unknown"
    assert legal.electrolyte_applicability == "unknown"
    with pytest.raises(ValidationError):
        Applicability(status="effective", applicability_note_zh="无证据不能确认")


@pytest.mark.parametrize("mode,method", [("live", "html_metadata"), ("fixture", "link_only")])
def test_demo_live_and_reuse_restrictions(mode, method):
    data = record() | {
        "data_mode": mode,
        "permitted_method": method,
        "evidence_snippets": [
            {
                "evidence_id": "e1",
                "source_url": "https://example.org/",
                "quote": "合成引用",
                "locator": "synthetic paragraph",
                "capture_mode": "fixture",
            }
        ],
    }
    with pytest.raises(ValidationError):
        IntelligenceRecord(**data)
