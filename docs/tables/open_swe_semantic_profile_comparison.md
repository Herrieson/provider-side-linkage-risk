| profiler | cluster_source | precision | recall | f1 | test_requests | threshold | min_request_support | embedding_seconds | max_rss_mb |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| structured_predicted_clusters | predicted | 0.823 | 0.791 | 0.807 | 3028 |  |  |  |  |
| semantic_predicted_clusters | predicted | 0.823 | 0.791 | 0.807 | 3028 | 0.580 | 3 | 106.656 | 2271.715 |
| semantic_truth_clusters | truth | 0.824 | 0.795 | 0.809 | 3028 | 0.580 | 3 | 106.656 | 2271.715 |

Calibration/test split: 124 / 432 disjoint orgs.
Evidence spans: 31950 total, 21507 unique.
Semantic-only predictions: 4; explicit artifact supported: 4.
The fixed benchmark truth does not include these artifact-supported additions, so they remain false positives in the quantitative table.
