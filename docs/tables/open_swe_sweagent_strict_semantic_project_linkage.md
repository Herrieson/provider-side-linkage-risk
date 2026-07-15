| scope | method | alpha_dense | sparse_floor | threshold | precision | recall | f1 | f1_ci_low | f1_ci_high | purity | split_rate | merge_rate | clusters | candidates | sessions | projects | embedding_seconds | tfidf_vocabulary |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| calibration_project_disjoint | dense_only | 1.000 | 0.000 | 0.840 | 1.000 | 0.031 | 0.061 |  |  | 1.000 | 0.245 | 0.000 | 119 | 2099 | 120 | 94 | 23.810 | 40000 |
| calibration_project_disjoint | structured_tfidf_only | 0.000 | 0.000 | 0.500 | 1.000 | 0.469 | 0.638 |  |  | 1.000 | 0.128 | 0.000 | 106 | 1863 | 120 | 94 | 23.810 | 40000 |
| calibration_project_disjoint | carp_content_project | 0.250 | 0.200 | 0.560 | 1.000 | 0.469 | 0.638 |  |  | 1.000 | 0.128 | 0.000 | 106 | 323 | 120 | 94 | 23.810 | 40000 |
| calibration_project_disjoint | carp_content_project | 0.250 | 0.300 | 0.560 | 1.000 | 0.469 | 0.638 |  |  | 1.000 | 0.128 | 0.000 | 106 | 86 | 120 | 94 | 23.810 | 40000 |
| calibration_project_disjoint | carp_content_project | 0.250 | 0.400 | 0.560 | 1.000 | 0.469 | 0.638 |  |  | 1.000 | 0.128 | 0.000 | 106 | 32 | 120 | 94 | 23.810 | 40000 |
| calibration_project_disjoint | carp_content_project | 0.500 | 0.200 | 0.600 | 1.000 | 0.500 | 0.667 |  |  | 1.000 | 0.170 | 0.000 | 110 | 305 | 120 | 94 | 23.810 | 40000 |
| calibration_project_disjoint | carp_content_project | 0.500 | 0.300 | 0.600 | 1.000 | 0.500 | 0.667 |  |  | 1.000 | 0.170 | 0.000 | 110 | 86 | 120 | 94 | 23.810 | 40000 |
| calibration_project_disjoint | carp_content_project | 0.500 | 0.400 | 0.600 | 1.000 | 0.312 | 0.476 |  |  | 1.000 | 0.181 | 0.000 | 111 | 32 | 120 | 94 | 23.810 | 40000 |
| calibration_project_disjoint | carp_content_project | 0.750 | 0.200 | 0.660 | 1.000 | 0.250 | 0.400 |  |  | 1.000 | 0.191 | 0.000 | 113 | 251 | 120 | 94 | 23.810 | 40000 |
| calibration_project_disjoint | carp_content_project | 0.750 | 0.300 | 0.660 | 1.000 | 0.250 | 0.400 |  |  | 1.000 | 0.191 | 0.000 | 113 | 74 | 120 | 94 | 23.810 | 40000 |
| calibration_project_disjoint | carp_content_project | 0.750 | 0.400 | 0.660 | 1.000 | 0.188 | 0.316 |  |  | 1.000 | 0.191 | 0.000 | 114 | 31 | 120 | 94 | 23.810 | 40000 |
| held_out_unseen_projects | strict_direct_anchor | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.179 | 0.000 | 380 | 0 | 380 | 280 | 23.810 | 40000 |
| held_out_unseen_projects | dense_only | 1.000 | 0.000 | 0.840 | 0.500 | 0.026 | 0.050 | 0.007 | 0.114 | 0.989 | 0.175 | 0.005 | 371 | 7140 | 380 | 280 | 23.810 | 40000 |
| held_out_unseen_projects | structured_tfidf_only | 0.000 | 0.000 | 0.500 | 0.307 | 0.423 | 0.356 | 0.196 | 0.540 | 0.937 | 0.111 | 0.010 | 307 | 6421 | 380 | 280 | 23.810 | 40000 |
| held_out_unseen_projects | carp_content_project | 0.500 | 0.300 | 0.600 | 0.942 | 0.286 | 0.439 | 0.274 | 0.592 | 0.992 | 0.129 | 0.009 | 335 | 948 | 380 | 280 | 23.810 | 40000 |
