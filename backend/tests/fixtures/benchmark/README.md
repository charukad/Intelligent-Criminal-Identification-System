# Benchmark Fixture Format

Use this folder structure when preparing a repeatable offline benchmark dataset:

```text
benchmark/
  person_a/
    image_01.jpg
    image_02.jpg
  person_b/
    image_01.jpg
    image_02.jpg
```

Rules:

- One directory per identity.
- Keep only one real person per directory.
- Include at least `2` images per identity.
- Prefer a mix of front, left, right, lighting, and expression changes.
- Do not mix enrollment images and benchmark holdout images unless you intend to measure that exact overlap.

Suggested workflow:

1. Build a manifest with `python scripts/build_pair_benchmark.py <dataset_root> --output-json <manifest.json>`.
2. Run the benchmark with `python scripts/run_recognition_benchmark.py <manifest.json>`.
3. Generate the governance report with `python scripts/generate_threshold_report.py <benchmark-report.json>`.
