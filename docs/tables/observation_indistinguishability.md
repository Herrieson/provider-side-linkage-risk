| entities_per_equivalence_class | equivalence_classes | requests | requests_per_entity | bayes_entity_accuracy_ceiling | expected_pairwise_precision_upper_bound | expected_pairwise_recall_upper_bound | expected_pairwise_f1_upper_bound | carp_precision | carp_recall | carp_f1 | carp_clusters | candidate_pair_events |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 100 | 400 | 4 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 100 | 1800 |
| 2 | 100 | 800 | 4 | 0.500 | 0.429 | 1.000 | 0.600 | 0.429 | 1.000 | 0.600 | 100 | 8400 |
| 4 | 100 | 1600 | 4 | 0.250 | 0.200 | 1.000 | 0.333 | 0.200 | 1.000 | 0.333 | 100 | 36000 |
| 8 | 100 | 3200 | 4 | 0.125 | 0.097 | 1.000 | 0.176 | 0.000 | 0.000 | 0.000 | 3200 | 49600 |
| 16 | 100 | 6400 | 4 | 0.062 | 0.048 | 1.000 | 0.091 | 0.000 | 0.000 | 0.000 | 6400 | 49600 |

Within each equivalence class, every entity has the same provider-visible sequence, 
with opaque request identifiers independent of entity. With `k` equal entities, closed-set entity 
accuracy is at most `1/k`. Retaining every true within-entity request pair requires 
merging the class. For `m` requests/entity, expected pairwise precision is bounded by 
`(m-1)/(km-1)`, recall by `1`, and F1 by `2(m-1)/(m(k+1)-2)`; merging the whole 
class attains the bound. The large-`m` limits are `1/k` and `2/(k+1)`. 
This is an observation-equivalence limit, not a claim about deployments that expose 
additional side information.
