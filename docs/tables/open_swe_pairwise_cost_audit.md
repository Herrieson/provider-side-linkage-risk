| method | actual_positive_pairs | actual_negative_pairs | positive_pair_prevalence | true_positive_pairs | false_positive_pairs | false_negative_pairs | pairwise_precision | pairwise_recall | pairwise_f1 | false_links_per_million_negative_pairs | pairwise_accuracy |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| singleton | 5400 | 6472800 | 0.000834 | 0 | 0 | 5400 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.999 |
| temporal | 5400 | 6472800 | 0.000834 | 444 | 3897 | 4956 | 0.102 | 0.082 | 0.091 | 602.058 | 0.999 |
| hybrid | 5400 | 6472800 | 0.000834 | 5392 | 176 | 8 | 0.968 | 0.999 | 0.983 | 27.191 | 1.000 |
| carp | 5400 | 6472800 | 0.000834 | 5400 | 368 | 0 | 0.936 | 1.000 | 0.967 | 56.853 | 1.000 |
| all_in_one | 5400 | 6472800 | 0.000834 | 5400 | 6472800 | 0 | 0.000834 | 1.000 | 0.001666 | 1000000.000 | 0.000834 |

Pairwise accuracy is dominated by true-negative request pairs: the singleton baseline 
can exceed 99.9% accuracy while recovering no true link. Pairwise precision instead 
asks what fraction of predicted links are correct, and recall asks what fraction of 
true links are recovered.

| false_positive_cost / false_negative_cost | method | weighted_error_per_true_pair |
| --- | --- | --- |
| 0.100 | singleton | 1.000 |
| 0.100 | temporal | 0.990 |
| 0.100 | hybrid | 0.004741 |
| 0.100 | carp | 0.006815 |
| 0.100 | all_in_one | 119.867 |
| 1.000 | singleton | 1.000 |
| 1.000 | temporal | 1.639 |
| 1.000 | hybrid | 0.034 |
| 1.000 | carp | 0.068 |
| 1.000 | all_in_one | 1198.667 |
| 10.000 | singleton | 1.000 |
| 10.000 | temporal | 8.134 |
| 10.000 | hybrid | 0.327 |
| 10.000 | carp | 0.681 |
| 10.000 | all_in_one | 11986.667 |
| 100.000 | singleton | 1.000 |
| 100.000 | temporal | 73.084 |
| 100.000 | hybrid | 3.261 |
| 100.000 | carp | 6.815 |
| 100.000 | all_in_one | 119866.667 |

The cost ratio is intentionally reported as a sensitivity parameter. False positives 
contaminate a pseudonymous profile or watchlist with unrelated traffic; false negatives 
understate the provider's aggregation reach. No single ratio is universal.
