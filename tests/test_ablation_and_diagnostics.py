from __future__ import annotations

import unittest

from agent_privacy.attacks.pipeline import hybrid_candidate_edges, run_attacks
from agent_privacy.experiments.ablations import apply_ablation
from agent_privacy.features.extract import extract_request_features


def _row(request_id: str, turn: int, include_repository: bool = True, include_workspace: bool = True) -> dict:
    parts = ["Fix failing auth test."]
    if include_repository:
        parts.append("repository=owner_alpha/project_api")
    if include_workspace:
        parts.append("workspace=/workspace/owner_alpha__project_api")
    tool_path = (
        "/workspace/owner_alpha__project_api/tests/test_auth.py"
        if include_workspace
        else "tests/test_auth.py"
    )
    return {
        "request_id": request_id,
        "timestamp": f"2026-01-05T09:{turn:02d}:00Z",
        "model": "generic-agent-model",
        "messages": [
            {"role": "system", "content": "You are an LLM coding agent."},
            {
                "role": "user",
                "content": " ".join(parts),
            },
            {
                "role": "tool",
                "name": "shell",
                "content": (
                    f"$ pytest {tool_path}\n"
                    f"trace_id=trace-alpha-project-{turn:02d}"
                ),
            },
        ],
        "tool_schemas": [{"name": "shell", "parameters": ["cmd"]}],
        "token_count": 20,
        "cache_bucket": None,
    }


class AblationAndDiagnosticsTest(unittest.TestCase):
    def test_no_workspace_paths_removes_workspace_repo_features(self) -> None:
        ablated = apply_ablation(
            [_row("r1", 1, include_repository=False, include_workspace=True)],
            "no_workspace_paths",
        )[0]
        text = "\n".join(message["content"] for message in ablated["messages"])
        features = extract_request_features(ablated)

        self.assertNotIn("/workspace/owner_alpha__project_api", text)
        self.assertFalse(any(value.startswith("repo_full:") for value in features.identifiers))

    def test_no_repo_ids_removes_repository_field_features(self) -> None:
        ablated = apply_ablation(
            [_row("r1", 1, include_repository=True, include_workspace=False)],
            "no_repo_ids",
        )[0]
        text = "\n".join(message["content"] for message in ablated["messages"])
        features = extract_request_features(ablated)

        self.assertNotIn("repository=owner_alpha/project_api", text)
        self.assertFalse(any(value.startswith("repo_full:") for value in features.identifiers))

    def test_no_repository_fields_preserves_workspace_features(self) -> None:
        ablated = apply_ablation(
            [_row("r1", 1, include_repository=True, include_workspace=True)],
            "no_repository_fields",
        )[0]
        text = "\n".join(message["content"] for message in ablated["messages"])
        features = extract_request_features(ablated)

        self.assertNotIn("repository=owner_alpha/project_api", text)
        self.assertIn("/workspace/owner_alpha__project_api", features.paths)
        self.assertIn("repo_full:owner_alpha/project_api", features.identifiers)

    def test_hybrid_candidate_edges_reports_link_reasons(self) -> None:
        rows = [_row("r1", 1), _row("r2", 2)]

        predictions = run_attacks(rows, methods=["hybrid"])
        edges = hybrid_candidate_edges(rows)

        self.assertIn("hybrid", predictions)
        self.assertTrue(edges)
        self.assertIn("session", edges[0]["links"])
        self.assertIn("project", edges[0]["links"])

    def test_feature_budget_preserves_tail_workspace_repo_signals(self) -> None:
        row = _row("r1", 1, include_repository=False, include_workspace=False)
        row["messages"][1]["content"] = (
            "filler " * 30_000
            + "repository=owner_tail/project_tail "
            + "workspace=/workspace/owner_tail__project_tail"
        )

        features = extract_request_features(row)

        self.assertIn("/workspace/owner_tail__project_tail", features.paths)
        self.assertIn("repo_full:owner_tail/project_tail", features.identifiers)


if __name__ == "__main__":
    unittest.main()
