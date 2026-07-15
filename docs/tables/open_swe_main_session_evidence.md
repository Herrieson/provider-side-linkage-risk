| scope | method | role | workflows | requests | precision | recall | f1 | purity | split_rate | merge_rate | clusters | f1_ci_low | f1_ci_high |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| heldout_900_workflows | temporal | time-only baseline | 900 | 3600 | 0.102 | 0.082 | 0.091 | 0.490 | 0.999 | 0.697 | 1384 | 0.082 | 0.099 |
| heldout_900_workflows | rare | rare-trace baseline | 900 | 3600 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 0.000 | 3600 | 0.000 | 0.000 |
| heldout_900_workflows | tool | tool-fingerprint baseline | 900 | 3600 | 0.001 | 1.000 | 0.002 | 0.001 | 0.000 | 1.000 | 1 | 0.002 | 0.002 |
| heldout_900_workflows | hybrid | high-fidelity baseline | 900 | 3600 | 0.968 | 0.999 | 0.983 | 0.988 | 0.002 | 0.012 | 892 | 0.966 | 0.996 |
| heldout_900_workflows | provider_lowcost | CARP | 900 | 3600 | 0.936 | 1.000 | 0.967 | 0.977 | 0.000 | 0.022 | 879 | 0.940 | 0.990 |
| heldout_900_workflows | hybrid_no_workspace | workspace-removal control | 900 | 3600 | 0.983 | 0.365 | 0.532 | 0.998 | 0.702 | 0.002 | 2518 | 0.503 | 0.563 |
| heldout_900_workflows | hybrid_turn_delta | non-cumulative Hybrid control | 900 | 3600 | 0.939 | 0.062 | 0.117 | 0.996 | 1.000 | 0.004 | 3288 | 0.105 | 0.130 |
| heldout_900_workflows | carp_turn_delta | non-cumulative CARP control | 900 | 3600 | 0.926 | 0.063 | 0.117 | 0.994 | 1.000 | 0.005 | 3281 | 0.105 | 0.130 |
| development_100_workflows | context_only | bounded context-only | 100 | 400 | 0.789 | 1.000 | 0.882 | 0.910 | 0.000 | 0.088 | 91 | 0.757 | 0.974 |
| development_100_workflows | provider_lowcost | CARP diagnostic | 100 | 400 | 0.789 | 1.000 | 0.882 | 0.910 | 0.000 | 0.088 | 91 | 0.757 | 0.974 |
| heldout_900_workflows | exact_message_nesting | exact cumulative-prefix baseline | 900 | 3600 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 900 | 1.000 | 1.000 |
| heldout_900_workflows | provider_lowcost_minus_hybrid | paired session-F1 difference | 900 | 3600 |  |  | -0.016 |  |  |  |  | -0.039 | -0.002 |

Held-out CARP ordering on 860 pure session clusters: adjacent accuracy 0.753 and pairwise accuracy 0.833 over 2580/5160 ordered pairs.

The development context-only row isolates bounded cumulative-context and identifier rules; it does not form project, owner, or cross-cache entity links.
