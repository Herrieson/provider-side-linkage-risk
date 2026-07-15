| method | requests | candidate_pairs | truth_session_pairs | candidate_recall | candidate_precision | exact_topk_pair_recall | session_precision | session_recall | session_f1 | purity | clusters | link_threshold | top_k | ef_search | ef_construction | max_connections | build_seconds | query_seconds | index_bytes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| exact_dense_topk | 1736 | 27128 | 8846 | 1.000 | 0.326 | 1.000 | 0.922 | 1.000 | 0.960 | 0.962 | 154 | 0.980 | 24 | exact | exact | exact | 0.000 | 0.000 | 2666496 |
| hnsw_ef16 | 1736 | 27540 | 8846 | 0.970 | 0.312 | 0.891 | 0.920 | 0.970 | 0.944 | 0.962 | 198 | 0.980 | 24 | 16 | 200 | 16 | 0.240 | 0.017 | 2925756 |
| hnsw_ef64 | 1736 | 27408 | 8846 | 0.985 | 0.318 | 0.911 | 0.921 | 0.985 | 0.952 | 0.962 | 176 | 0.980 | 24 | 64 | 200 | 16 | 0.229 | 0.034 | 2925756 |
| hnsw_ef200 | 1736 | 27342 | 8846 | 0.993 | 0.321 | 0.933 | 0.922 | 0.993 | 0.956 | 0.962 | 165 | 0.980 | 24 | 200 | 200 | 16 | 0.236 | 0.089 | 2925756 |
