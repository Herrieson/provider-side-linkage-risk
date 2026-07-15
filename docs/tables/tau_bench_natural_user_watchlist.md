| condition | early_workflows | later_workflows | early_users | later_seen_user_workflows | assigned_later_workflows | matched_eligible_workflows | correct_assignments | ambiguous_later_workflows | watchlist_anchors | early_components | pure_component_rate | precision | recall | f1 | f1_ci_low | f1_ci_high |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| all_identity_anchors | 100 | 100 | 53 | 64 | 64 | 64 | 64 | 0 | 123 | 57 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| uid_only | 100 | 100 | 53 | 64 | 64 | 64 | 64 | 0 | 50 | 57 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| cross_alias_no_later_uid | 100 | 100 | 53 | 64 | 62 | 62 | 62 | 0 | 123 | 57 | 1.000 | 1.000 | 0.969 | 0.984 | 0.959 | 1.000 |
| cross_alias_namezip_only | 100 | 100 | 53 | 64 | 29 | 29 | 29 | 0 | 123 | 57 | 1.000 | 1.000 | 0.453 | 0.624 | 0.505 | 0.729 |
| strict_later_semantic_intent | 100 | 100 | 53 | 64 | 25 | 25 | 23 | 0 | 123 | 57 | 1.000 | 0.920 | 0.359 | 0.517 | 0.379 | 0.643 |
| strict_semantic_base_task_disjoint | 101 | 99 | 44 | 25 | 35 | 14 | 8 | 0 | 114 | 45 | 1.000 | 0.229 | 0.320 | 0.267 | 0.131 | 0.415 |
