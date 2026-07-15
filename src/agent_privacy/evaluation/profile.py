from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


def evaluate_profiles(
    predicted_profiles: dict[str, dict[str, Any]],
    truth_rows: list[dict[str, Any]],
    labels: dict[str, str],
) -> list[dict[str, Any]]:
    truth_by_request = {row["request_id"]: row for row in truth_rows}
    org_truth = _org_truth(truth_rows)
    predicted_by_org: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))

    for profile in predicted_profiles.values():
        request_ids = profile["request_ids"]
        majority_org = _majority_org(request_ids, truth_by_request)
        if majority_org is None or majority_org.startswith("noise_"):
            continue
        for field, values in profile.get("fields", {}).items():
            predicted_by_org[majority_org][field].update(values)

    totals: dict[str, Counter[str]] = defaultdict(Counter)
    evidence_totals: dict[str, Counter[str]] = defaultdict(Counter)

    for majority_org in sorted(set(org_truth) | set(predicted_by_org)):
        fields = predicted_by_org[majority_org]
        for field in sorted(set(fields) | set(org_truth[majority_org])):
            pred_values = set(fields.get(field, []))
            truth_values = set(org_truth[majority_org].get(field, []))
            totals[field]["tp"] += len(pred_values & truth_values)
            totals[field]["fp"] += len(pred_values - truth_values)
            totals[field]["fn"] += len(truth_values - pred_values)

    for profile in predicted_profiles.values():
        evidence = profile.get("evidence", {})
        for field, values in profile.get("fields", {}).items():
            evidence_totals[field]["predicted_values"] += len(values)
            for value in values:
                if evidence.get(field, {}).get(value):
                    evidence_totals[field]["evidenced_values"] += 1
                else:
                    evidence_totals[field]["unsupported_predictions"] += 1

    rows: list[dict[str, Any]] = []
    for field, counts in sorted(totals.items()):
        precision = _ratio(counts["tp"], counts["tp"] + counts["fp"])
        recall = _ratio(counts["tp"], counts["tp"] + counts["fn"])
        f1 = _f1(precision, recall)
        evidence_counts = evidence_totals[field]
        rows.append(
            {
                "field": field,
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "tp": counts["tp"],
                "fp": counts["fp"],
                "fn": counts["fn"],
                "predicted_values": evidence_counts["predicted_values"],
                "evidenced_values": evidence_counts["evidenced_values"],
                "unsupported_predictions": evidence_counts["unsupported_predictions"],
                "evidence_coverage": _ratio(
                    evidence_counts["evidenced_values"],
                    evidence_counts["predicted_values"],
                ),
            }
        )
    micro = Counter()
    for counts in totals.values():
        micro.update(counts)
    evidence_micro = Counter()
    for counts in evidence_totals.values():
        evidence_micro.update(counts)
    precision = _ratio(micro["tp"], micro["tp"] + micro["fp"])
    recall = _ratio(micro["tp"], micro["tp"] + micro["fn"])
    rows.append(
        {
            "field": "__micro__",
            "precision": precision,
            "recall": recall,
            "f1": _f1(precision, recall),
            "tp": micro["tp"],
            "fp": micro["fp"],
            "fn": micro["fn"],
            "predicted_values": evidence_micro["predicted_values"],
            "evidenced_values": evidence_micro["evidenced_values"],
            "unsupported_predictions": evidence_micro["unsupported_predictions"],
            "evidence_coverage": _ratio(
                evidence_micro["evidenced_values"],
                evidence_micro["predicted_values"],
            ),
        }
    )
    return rows


def _org_truth(truth_rows: list[dict[str, Any]]) -> dict[str, dict[str, set[str]]]:
    out: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for row in truth_rows:
        org_id = row["org_id"]
        if org_id.startswith("noise_"):
            continue
        for field, values in row.get("profile_truth", {}).items():
            out[org_id][field].update(values)
    return out


def _majority_org(request_ids: list[str], truth_by_request: dict[str, dict[str, Any]]) -> str | None:
    counts = Counter(truth_by_request[request_id]["org_id"] for request_id in request_ids if request_id in truth_by_request)
    return counts.most_common(1)[0][0] if counts else None


def _ratio(num: int, den: int) -> float:
    return num / den if den else 0.0


def _f1(precision: float, recall: float) -> float:
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0
