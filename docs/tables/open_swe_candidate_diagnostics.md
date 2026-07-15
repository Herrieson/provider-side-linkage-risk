| stage | candidate_pairs | true_session_pairs_retained | truth_session_pairs | candidate_recall | candidate_precision | feature_window_chars | max_shingles | max_words | sketch_size | band_size | session_precision | session_recall | session_f1 | purity | split_rate | merge_rate | clusters |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rare_candidates | 0 | 0 | 5400 | 0.000 | 0.000 | 24000 | 1200 | 1500 |  |  |  |  |  |  |  |  |  |
| context_candidates | 27904 | 5400 | 5400 | 1.000 | 0.194 | 24000 | 1200 | 1500 |  |  |  |  |  |  |  |  |  |
| refine_candidates | 16947 | 5397 | 5400 | 0.999 | 0.318 | 24000 | 1200 | 1500 |  |  |  |  |  |  |  |  |  |
| candidate_union | 31473 | 5400 | 5400 | 1.000 | 0.172 | 24000 | 1200 | 1500 |  |  |  |  |  |  |  |  |  |
| bottom_k_shingle_sketch_candidates | 46087 | 5345 | 5400 | 0.990 | 0.116 | 24000 | 1200 | 1500 | 32 | 4 |  |  |  |  |  |  |  |
| bottom_k_shingle_sketch_linkage | 46087 | 5345 | 5400 | 0.990 | 0.116 | 24000 | 1200 | 1500 | 32 | 4 | 0.756 | 0.991 | 0.858 | 0.917 | 0.013 | 0.063 | 843 |
| carp_final | 31473 | 5400 | 5400 | 1.000 | 0.172 | 24000 | 1200 | 1500 |  |  | 0.936 | 1.000 | 0.967 | 0.977 | 0.000 | 0.022 | 879 |
| hybrid_final |  |  | 5400 |  |  | 24000 | 1200 | 1500 |  |  | 0.968 | 0.999 | 0.983 | 0.988 | 0.002 | 0.012 | 892 |
