from __future__ import annotations

from pathlib import Path

import pytest

from agent_privacy.data.fidelity import (
    DatasetFidelityManifest,
    FieldFidelity,
    FidelityLevel,
)
from agent_privacy.data.trace_transform import (
    TraceTransformOptions,
    transform_trace_rows,
    validate_trace_preservation,
)
from agent_privacy.evaluation.fidelity import fidelity_audit
from agent_privacy.io import read_jsonl


SMOKE = Path("examples/tool_agent_smoke/dataset/attack_view.jsonl")


def test_fidelity_manifest_round_trip_and_exactness_guard() -> None:
    manifest = DatasetFidelityManifest(
        dataset_id="smoke",
        level=FidelityLevel.F1,
        source="public trajectory",
        fields=(
            FieldFidelity(
                field="messages",
                level=FidelityLevel.F1,
                source="trajectory prefixes",
            ),
        ),
        timestamp_status="controlled schedule",
        transformations=("stable typed-handle pseudonymization",),
        unsupported_claims=("real provider timestamps",),
    )
    assert DatasetFidelityManifest.from_dict(manifest.to_dict()) == manifest
    invalid = FieldFidelity(
        field="messages",
        level=FidelityLevel.F3,
        source="payload",
        transformed=True,
    )
    with pytest.raises(ValueError):
        invalid.validate()


def test_trace_transform_is_span_auditable_and_structure_preserving() -> None:
    rows = read_jsonl(SMOKE)
    transformed, lineage = transform_trace_rows(rows)
    validation = validate_trace_preservation(rows, transformed, lineage)
    assert validation["requests"] == 6
    assert validation["edits"] > 0
    assert validation["edited_character_ratio"] > 0.0
    source_text = str(rows)
    transformed_text = str(transformed)
    assert "customer_alpha001" in source_text
    assert "customer_alpha001" not in transformed_text
    assert all("edits" not in row and "fidelity_level" not in row for row in transformed)
    audit = fidelity_audit(rows, transformed)
    assert audit["role_sequence_preservation"] == 1.0
    assert audit["tool_sequence_preservation"] == 1.0
    assert all(value == 0.0 for value in audit["categorical_js"].values())


def test_identity_fidelity_audit_is_zero_divergence_and_chance_auc() -> None:
    rows = read_jsonl(SMOKE)
    audit = fidelity_audit(rows, rows)
    assert audit["two_sample_auc"] == 0.5
    assert all(value == 0.0 for value in audit["categorical_js"].values())
    assert all(value == 0.0 for value in audit["numeric_ks"].values())


def test_transform_scope_controls_stability() -> None:
    rows = read_jsonl(SMOKE)[:2]
    stable, _ = transform_trace_rows(rows, TraceTransformOptions(scope="dataset"))
    per_request, _ = transform_trace_rows(rows, TraceTransformOptions(scope="request"))
    assert "order_p000001" in str(stable[0])
    assert "order_p000001" in str(stable[1])
    assert str(per_request[0]) != str(per_request[1])
