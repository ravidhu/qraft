# Compilation Benchmarks

Qraft's core compilation pipeline — SQL parsing, DAG construction, variable resolution, and DDL wrapping — is written in Rust and exposed to Python via PyO3. This page documents benchmark results to quantify that performance.

## What's measured

The full compilation pipeline, broken into phases:

1. **Parse** — Extract front-matter, `ref()`, `source()`, and `{{ var }}` from raw SQL (regex-based, Rust)
2. **DAG** — Build dependency graph, validate, topological sort (petgraph, Rust)
3. **Compile** — Resolve variables, expand refs/sources, handle ephemerals, wrap DDL (batch Rust calls)

No database I/O is involved — this is pure compilation performance.

## Setup

- **Machine:** Apple M1 Max, 64 GB RAM
- **Runtime:** Python 3.13, Rust (release build via PyO3)
- **Methodology:** Median of 10 runs, 2 warmup runs discarded
- **Script:** [`scripts/benchmark.py`](../scripts/benchmark.py)

## Real-world example projects

| Project | Models | Parse | DAG | Compile | Total | Per model |
|---------|-------:|------:|----:|--------:|------:|----------:|
| blog_analytics | 5 | 0.02ms | 0.02ms | 1.41ms | **1.30ms** | 0.26ms |
| ecommerce_basic | 8 | 0.02ms | 0.03ms | 2.38ms | **2.17ms** | 0.27ms |
| postgres_to_duckdb | 5 | 0.01ms | 0.01ms | 1.17ms | **1.17ms** | 0.23ms |
| saas_analytics | 17 | 0.03ms | 0.04ms | 4.50ms | **4.60ms** | 0.27ms |

## Scale test (synthetic linear DAG)

To test scaling behavior, synthetic models are generated with a linear dependency chain (each model refs the previous one).

| Models | Parse | DAG | Total | Per model |
|-------:|------:|----:|------:|----------:|
| 10 | 0.01ms | 0.01ms | **2.29ms** | 0.23ms |
| 50 | 0.04ms | 0.07ms | **11.58ms** | 0.23ms |
| 100 | 0.09ms | 0.14ms | **23.52ms** | 0.24ms |
| 200 | 0.18ms | 0.27ms | **48.28ms** | 0.24ms |
| 500 | 0.43ms | 0.69ms | **131.54ms** | 0.26ms |
| 1000 | 0.88ms | 1.37ms | **292.46ms** | 0.29ms |

## Key takeaways

- **Parsing + DAG is sub-millisecond** even for 17 models
- **~0.25ms per model** — near-linear scaling with no degradation up to 1,000 models
- **1,000 models compiled in under 300ms** — the entire parse, DAG, and compile pipeline
- **17-model real project compiles in 4.6ms** — effectively instant feedback

## Reproducing

Run the benchmark yourself:

```bash
maturin develop --release
uv run python scripts/benchmark.py
```
