from __future__ import annotations

import unittest

from agent_privacy.defenses.utility import summarize_utility


class UtilityMetricsTest(unittest.TestCase):
    def test_summarize_utility_counts_retention_and_removed_markers(self) -> None:
        original = [
            {
                "request_id": "req_1",
                "messages": [
                    {
                        "role": "user",
                        "content": "repo repository=owner/repo in /workspace/owner__repo/app.py",
                    },
                    {"role": "tool", "content": "token sk-test-ABCDEFGHIJKLMNOP"},
                ],
            }
        ]
        transformed = [
            {
                "request_id": "req_1",
                "messages": [
                    {"role": "user", "content": "repo repository=[REPO_REMOVED] in [PATH]"},
                    {"role": "tool", "content": "token [SECRET]"},
                ],
            }
        ]

        row = summarize_utility(original, transformed, defense="M2", ablation="none")

        self.assertEqual(row["requests_compared"], 1)
        self.assertLess(row["char_retention"], 1.0)
        self.assertEqual(row["path_count_removed"], 1)
        self.assertEqual(row["workspace_path_count_removed"], 1)
        self.assertEqual(row["raw_secret_count_removed"], 1)
        self.assertEqual(row["secret_placeholder_count_transformed"], 1)


if __name__ == "__main__":
    unittest.main()
