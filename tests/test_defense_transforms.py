from __future__ import annotations

import unittest

from agent_privacy.defenses.transforms import apply_defense


class DefenseTransformsTest(unittest.TestCase):
    def test_workspace_stable_pseudonym_keeps_same_slug_consistent(self) -> None:
        rows = [
            _row("req_1", "/workspace/owner__repo/a.py and /workspace/owner__repo/b.py"),
            _row("req_2", "/workspace/owner__repo/c.py"),
        ]

        defended = apply_defense(rows, "M7_WORKSPACE_STABLE")
        texts = [_text(row) for row in defended]

        self.assertNotIn("owner__repo", "\n".join(texts))
        self.assertIn("/workspace/workspace_0001/a.py", texts[0])
        self.assertIn("/workspace/workspace_0001/b.py", texts[0])
        self.assertIn("/workspace/workspace_0001/c.py", texts[1])

    def test_workspace_session_pseudonym_changes_across_requests(self) -> None:
        rows = [
            _row("req_1", "/workspace/owner__repo/a.py"),
            _row("req_2", "/workspace/owner__repo/a.py"),
        ]

        defended = apply_defense(rows, "M8_WORKSPACE_SESSION")
        texts = [_text(row) for row in defended]

        self.assertNotIn("owner__repo", "\n".join(texts))
        self.assertIn("/workspace/workspace_req_000001_001/a.py", texts[0])
        self.assertIn("/workspace/workspace_req_000002_001/a.py", texts[1])

    def test_workspace_path_type_only_removes_path_tail(self) -> None:
        rows = [_row("req_1", "open /workspace/owner__repo/src/app.py now")]

        defended = apply_defense(rows, "M9_PATH_TYPE_ONLY")

        self.assertEqual(_text(defended[0]), "open [WORKSPACE_PATH] now")


def _row(request_id: str, content: str) -> dict[str, object]:
    return {
        "request_id": request_id,
        "timestamp": "2026-01-01T00:00:00Z",
        "messages": [{"role": "tool", "content": content}],
    }


def _text(row: dict[str, object]) -> str:
    messages = row["messages"]
    assert isinstance(messages, list)
    return str(messages[0]["content"])


if __name__ == "__main__":
    unittest.main()
