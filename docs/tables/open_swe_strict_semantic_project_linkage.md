| scope | method | alpha_dense | sparse_floor | threshold | precision | recall | f1 | f1_ci_low | f1_ci_high | purity | split_rate | merge_rate | clusters | candidates | sessions | projects | embedding_seconds | tfidf_vocabulary |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| calibration_project_disjoint | dense_only | 1.000 | 0.000 | 0.860 | 1.000 | 0.015 | 0.030 |  |  | 1.000 | 0.269 | 0.000 | 234 | 4184 | 236 | 160 | 41.480 | 40000 |
| calibration_project_disjoint | structured_tfidf_only | 0.000 | 0.000 | 0.460 | 0.967 | 0.446 | 0.611 |  |  | 0.996 | 0.150 | 0.005 | 192 | 3885 | 236 | 160 | 41.480 | 40000 |
| calibration_project_disjoint | carp_content_project | 0.250 | 0.200 | 0.440 | 0.974 | 0.585 | 0.731 |  |  | 0.996 | 0.138 | 0.005 | 186 | 182 | 236 | 160 | 41.480 | 40000 |
| calibration_project_disjoint | carp_content_project | 0.250 | 0.300 | 0.440 | 0.974 | 0.585 | 0.731 |  |  | 0.996 | 0.138 | 0.005 | 186 | 108 | 236 | 160 | 41.480 | 40000 |
| calibration_project_disjoint | carp_content_project | 0.250 | 0.400 | 0.440 | 0.971 | 0.515 | 0.673 |  |  | 0.996 | 0.144 | 0.005 | 188 | 73 | 236 | 160 | 41.480 | 40000 |
| calibration_project_disjoint | carp_content_project | 0.500 | 0.200 | 0.440 | 0.970 | 0.754 | 0.848 |  |  | 0.992 | 0.100 | 0.011 | 175 | 181 | 236 | 160 | 41.480 | 40000 |
| calibration_project_disjoint | carp_content_project | 0.500 | 0.300 | 0.440 | 0.967 | 0.669 | 0.791 |  |  | 0.992 | 0.125 | 0.011 | 179 | 108 | 236 | 160 | 41.480 | 40000 |
| calibration_project_disjoint | carp_content_project | 0.500 | 0.400 | 0.480 | 0.971 | 0.508 | 0.667 |  |  | 0.996 | 0.150 | 0.005 | 189 | 73 | 236 | 160 | 41.480 | 40000 |
| calibration_project_disjoint | carp_content_project | 0.750 | 0.200 | 0.520 | 0.969 | 0.731 | 0.833 |  |  | 0.992 | 0.106 | 0.011 | 177 | 166 | 236 | 160 | 41.480 | 40000 |
| calibration_project_disjoint | carp_content_project | 0.750 | 0.300 | 0.460 | 0.960 | 0.731 | 0.830 |  |  | 0.987 | 0.106 | 0.017 | 174 | 102 | 236 | 160 | 41.480 | 40000 |
| calibration_project_disjoint | carp_content_project | 0.750 | 0.400 | 0.440 | 0.971 | 0.523 | 0.680 |  |  | 0.996 | 0.144 | 0.005 | 188 | 71 | 236 | 160 | 41.480 | 40000 |
| held_out_unseen_projects | strict_direct_anchor | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.292 | 0.000 | 764 | 0 | 764 | 479 | 41.480 | 40000 |
| held_out_unseen_projects | dense_only | 1.000 | 0.000 | 0.860 | 0.966 | 0.036 | 0.070 | 0.012 | 0.169 | 0.999 | 0.290 | 0.001 | 747 | 14104 | 764 | 479 | 41.480 | 40000 |
| held_out_unseen_projects | structured_tfidf_only | 0.000 | 0.000 | 0.460 | 1.000 | 0.204 | 0.339 | 0.254 | 0.433 | 1.000 | 0.223 | 0.000 | 670 | 12837 | 764 | 479 | 41.480 | 40000 |
| held_out_unseen_projects | carp_content_project | 0.500 | 0.200 | 0.440 | 0.795 | 0.597 | 0.682 | 0.578 | 0.772 | 0.955 | 0.132 | 0.033 | 544 | 992 | 764 | 479 | 41.480 | 40000 |
