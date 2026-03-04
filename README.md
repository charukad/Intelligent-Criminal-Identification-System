# TraceIQ: Intelligent Criminal Identification System

TraceIQ is a comprehensive efficient criminal identification system designed for law enforcement agencies. It combines advanced facial recognition with robust record management.

## Project Structure

### Backend (`/backend`)
Follows Domain-Driven Design (DDD):
*   `src/domain`: Core business logic and models.
*   `src/services`: Application services (orchestrator, agents).
*   `src/infrastructure`: Database and external implementations.
*   `src/api`: REST API endpoints (FastAPI).

### Frontend (`/frontend`)
Follows Feature-based architecture:
*   `src/components/orbit`: 3D/Visual components.
*   `src/store`: Zustand state management.
*   `src/lib`: API clients and utilities.

## Getting Started

1.  **Backend Setup**:
    ```bash
    cd backend
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

2.  **Frontend Setup**:
    ```bash
    cd frontend
    npm install
    npm run dev
    ```

## Documentation
*   `project_overview.md`: Comprehensive technical specification.
*   `ai_architecture.md`: Details on the AI/ML pipeline.

## Benchmark Workflow

The repo now includes an offline benchmark workflow for threshold calibration and rollout review:

1. Build a benchmark manifest from an identity-labelled image folder:
   ```bash
   cd backend
   python scripts/build_pair_benchmark.py /path/to/benchmark-dataset --output-json uploads/benchmarks/local-manifest.json
   ```
2. Run the benchmark with the current runtime stack:
   ```bash
   python scripts/run_recognition_benchmark.py uploads/benchmarks/local-manifest.json
   ```
   You can also evaluate a specific embedding version:
   ```bash
   python scripts/run_recognition_benchmark.py uploads/benchmarks/local-manifest.json --embedding-version facenet_vggface2
   ```
3. Generate the threshold and release recommendation report:
   ```bash
   python scripts/generate_threshold_report.py uploads/benchmarks/<benchmark-report>.json
   ```
4. Enforce the release gate before a threshold or model rollout:
   ```bash
   python scripts/check_benchmark_gate.py uploads/benchmarks/<threshold-report>.json
   ```

Benchmark dataset layout is documented in `backend/tests/fixtures/benchmark/README.md`.

## Model Upgrade Workflow

The repo now includes the first `M7` model-upgrade path for comparing embedders and safely re-embedding stored faces.

1. Compare supported models on the same held-out manifest:
   ```bash
   cd backend
   python scripts/compare_models.py uploads/benchmarks/face-2-heldout-manifest.json \
     --output-json uploads/benchmarks/face-2-model-comparison.json \
     --output-markdown uploads/benchmarks/face-2-model-comparison.md
   ```
2. Inspect the winner and threshold report artifacts under `uploads/benchmarks/comparisons/<dataset-name>/`.
3. Dry-run a re-embedding plan before changing stored vectors:
   ```bash
   python scripts/reembed_all_faces.py --target-version facenet_vggface2 --dry-run
   ```
4. Run the actual migration with an automatic snapshot backup:
   ```bash
   python scripts/reembed_all_faces.py --target-version facenet_vggface2
   ```
5. Roll back from a snapshot if needed:
   ```bash
   python scripts/reembed_all_faces.py --rollback-json uploads/migration-backups/<snapshot>.json
   ```

Current held-out result:
- `tracenet_v1`: `no_go`
- `facenet_vggface2`: `go`

The Docker backend now reads `FACE_EMBEDDING_VERSION`, and `docker-compose.yml` defaults that runtime setting to `facenet_vggface2`.
# Intelligent-Criminal-Identification-System
