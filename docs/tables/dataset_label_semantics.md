# Dataset-Specific Label Semantics

| Dataset | Evaluation slot | Actual label meaning | A successful result supports | It does not support |
| --- | --- | --- | --- | --- |
| Open-SWE | session/workflow | one adapted agent trajectory | recovery of workflow continuity from repeated requests | natural-person identity or a unique human operator |
| Open-SWE | project | GitHub repository | direct repository exposure or cross-workflow association through a repository anchor | hidden enterprise project inference |
| Open-SWE | owner | GitHub owner-like slug | direct owner exposure or cross-workflow association through an owner anchor | legal company, tenant, or customer identification |
| Historical tau-bench | session/workflow | one benchmark dialogue/tool trajectory | partial, timestamp-sensitive trajectory association | real airline/retail customer recovery or production prevalence |
| Historical tau-bench | user/project/org | upstream benchmark proxy fields | descriptive audit only | reliable real-world hierarchical entity reconstruction |
| Dataset B U3/U4 | user/project/org | controlled labels injected over Open-SWE traces | mechanism behavior when user/environment signals are distinguishable or shared | real Open-SWE user identities |
| T3 overlay | user/customer-like | synthetic customer assignment over real tau-bench trajectories | controlled typed-anchor percolation and watchlist behavior | real customer re-identification |
| T3 overlay | project/process | synthetic business-project assignment | controlled cross-cache business-object association | recovery of an upstream tau-bench business process label |
| T3 overlay | tenant/owner-like | synthetic tenant assignment | controlled long-lived component propagation | enterprise organization identification |
| Open-SWE profile | technical fields | fixed audited ontology over repository/owner-like groups | accumulation of partial technical evidence | complete enterprise profiling or a generative-profiler upper bound |

The paper uses the four evaluation slots as a common reporting interface only. They are not a
universal enterprise hierarchy and are never interpreted as natural-person identity truth.
