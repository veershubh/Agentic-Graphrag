# Local resource snapshot

Measured on 2026-10-20 during full-inventory graph extraction on an NVIDIA GeForce RTX 4050 Laptop GPU.

## Active extraction sample

Twelve one-second samples were collected during active Qwen3 4B extraction:

| Measure | Observed |
|---|---:|
| GPU memory in use | 3,145 MiB of 6,141 MiB |
| GPU utilization | 62–96%, mean 92.25% |
| GPU board power | 63.17–75.20 W, mean 72.88 W |
| Extraction Python processes working set | 22.4 MiB combined in the sample |

## Latency sample

The 50 most recent completed extraction cache entries at the sample time had a mean model-call latency of 10.41s (median 8.09s, range 0.54–19.08s; 520.5s total). A separate local one-hop agent query took 94.45s end to end; its planner, retrieval, and answer timings are in [the trace review](agent-trace-failure.md). Local model API charges were $0.

These are workload snapshots, not whole-device energy measurements or a full-run performance profile. GPU board power excludes other laptop components; results depend on the active model and hardware state. The full extraction cost/time summary will be recorded when the 3,203-passage run finishes.
