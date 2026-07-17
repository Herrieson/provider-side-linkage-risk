# Agent-Native Evidence Ablations

| Dataset | Variant | Precision | Recall | F1 | Edge precision | Coverage | Abstention | Contaminated requests | Candidates/request |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| open_swe_traces_raw_1000_turn_delta_3_6_9_12_sample100 | full | 1.000 | 0.245 | 0.394 | 1.000 | 0.390 | 0.703 | 0 | 5.09 |
| open_swe_traces_raw_1000_turn_delta_3_6_9_12_sample100 | replay_only | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.995 | 0 | 5.09 |
| open_swe_traces_raw_1000_turn_delta_3_6_9_12_sample100 | tool_resource_only | 1.000 | 0.222 | 0.363 | 1.000 | 0.370 | 0.713 | 0 | 5.09 |
| open_swe_traces_raw_1000_turn_delta_3_6_9_12_sample100 | typed_handle_only | 1.000 | 0.005 | 0.010 | 1.000 | 0.010 | 0.980 | 0 | 5.09 |
| open_swe_traces_raw_1000_turn_delta_3_6_9_12_sample100 | without_conflicts | 1.000 | 0.245 | 0.394 | 1.000 | 0.390 | 0.708 | 0 | 5.09 |
| tau_bench_historical_sample200 | full | 1.000 | 0.090 | 0.164 | 1.000 | 0.374 | 0.646 | 0 | 23.97 |
| tau_bench_historical_sample200 | replay_only | 1.000 | 0.018 | 0.035 | 1.000 | 0.101 | 0.894 | 0 | 23.97 |
| tau_bench_historical_sample200 | tool_resource_only | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.434 | 0 | 23.97 |
| tau_bench_historical_sample200 | typed_handle_only | 1.000 | 0.034 | 0.066 | 1.000 | 0.145 | 0.650 | 0 | 23.97 |
| tau_bench_historical_sample200 | without_conflicts | 1.000 | 0.090 | 0.164 | 1.000 | 0.374 | 0.660 | 0 | 23.97 |
