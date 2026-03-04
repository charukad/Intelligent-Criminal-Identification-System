# TraceIQ Testing Plan

This document outlines the systematic testing strategy for the TraceIQ application. Each feature will be tested manually and/or automatically to ensure functionality and stability.

## 🟢 1. Authentication & Session Management
- [ ] **Login with valid credentials**
  - **Input:** `admin` / `admin123`
  - **Expected:** Redirect to Dashboard, JWT token stored in localStorage/cookies.
- [ ] **Login with invalid credentials**
  - **Input:** `admin` / `wrongpass`
  - **Expected:** Error message "Invalid credentials", stay on login page.
- [ ] **Access protected route without login**
  - **Action:** Navigate to `/dashboard` directly in private window.
  - **Expected:** Redirect to `/login`.
- [ ] **Logout**
  - **Action:** Click "Logout" in user menu.
  - **Expected:** Redirect to `/login`, token cleared.

## 🟢 2. Dashboard & Navigation
- [ ] **Dashboard Loading**
  - **Action:** Load `/dashboard`.
  - **Expected:** Render sidebar, stats cards, recent activity without crashing.
- [ ] **Sidebar Navigation**
  - **Action:** Click "Criminals", "Cases", "Users".
  - **Expected:** URL changes, correct active state in sidebar, page content renders.
- [ ] **User Profile Menu**
  - **Action:** Click user avatar.
  - **Expected:** Dropdown appears with "Profile", "Settings", "Logout".

## 🟡 3. User Management (Admin Only)
- [ ] **List Users**
  - **Action:** Navigate to `/users`.
  - **Expected:** Table displays list of users (at least `admin` should be there).
- [ ] **Create User**
  - **Action:** Click "Add User", fill form (Officer Name, Role: Field Officer).
  - **Expected:** User created, appears in list.
- [ ] **Edit User**
  - **Action:** Change role or status of created user.
  - **Expected:** Updates reflected.

## 🟡 4. Criminal Record Management (Core Functionality)
- [ ] **List Criminals**
  - **Action:** Navigate to `/criminals`.
  - **Expected:** Table displays criminals (empty initially).
- [ ] **Create Criminal Profile**
  - **Action:** Click "New Profile", fill mandatory fields (Name, NIC, Gender).
  - **Expected:** Profile created, redirected to detail view.
- [ ] **Search Criminals**
  - **Action:** Type name/NIC in search bar.
  - **Expected:** filtered results.
- [ ] **View Profile (Dossier)**
  - **Action:** Click on a criminal.
  - **Expected:** Detailed view showing info, offenses, mugshots.

## 🟡 5. Case Management
- [ ] **List Cases**
  - **Action:** Navigate to `/cases`.
  - **Expected:** List of active cases.
- [ ] **Create Case**
  - **Action:** Create new case, assign lead officer.
  - **Expected:** Case created.

## 🔴 6. AI & Face Recognition (Known Issues)
- [ ] **Face Embedding Generation**
  - **Current Status:** **BLOCKED** (pgvector missing).
  - **Test:** Verify app handles this gracefully (e.g., specific error message or disabled feature) rather than crashing the whole backend.

## 🟠 7. Offline Benchmark Governance
- [ ] **Prepare benchmark dataset manifest**
  - **Action:** Organize a directory with one subdirectory per identity and at least 2 images per person, then run:
    ```bash
    cd backend
    python scripts/build_pair_benchmark.py /path/to/benchmark-dataset --output-json uploads/benchmarks/local-manifest.json
    ```
  - **Expected:** JSON manifest created with deterministic positive and negative pairs.
- [ ] **Run offline benchmark**
  - **Action:** Execute:
    ```bash
    python scripts/run_recognition_benchmark.py uploads/benchmarks/local-manifest.json
    ```
  - **Expected:** Benchmark JSON created with pair metrics, template calibration, and recommended policy thresholds.
- [ ] **Generate go/no-go threshold report**
  - **Action:** Execute:
    ```bash
    python scripts/generate_threshold_report.py uploads/benchmarks/<benchmark-report>.json --output-markdown uploads/benchmarks/<threshold-report>.md
    ```
  - **Expected:** Governance report created with a `go`, `conditional`, or `no_go` decision plus rollout checklist.
- [ ] **Block unreviewed threshold changes**
  - **Action:** Before changing recognition thresholds or deploying a new model, attach the latest benchmark JSON and threshold report to the release note.
  - **Expected:** The release gate command fails when the report is stale, mismatched, or `no_go`.
    ```bash
    python scripts/check_benchmark_gate.py uploads/benchmarks/<threshold-report>.json
    ```

## 🟠 8. Model Upgrade Path
- [ ] **Compare supported embedding models on the same held-out manifest**
  - **Action:** Execute:
    ```bash
    cd backend
    python scripts/compare_models.py uploads/benchmarks/face-2-heldout-manifest.json --output-json uploads/benchmarks/face-2-model-comparison.json
    ```
  - **Expected:** A comparison report is generated with per-model benchmark artifacts and a recommended winner.
- [ ] **Verify benchmark winner before runtime switch**
  - **Action:** Inspect `uploads/benchmarks/face-2-model-comparison.json`.
  - **Expected:** The selected runtime model has a `go` decision and a better top-1 rate than the previous version.
- [ ] **Dry-run re-embedding plan**
  - **Action:** Execute:
    ```bash
    python scripts/reembed_all_faces.py --target-version facenet_vggface2 --dry-run
    ```
  - **Expected:** The command returns an eligibility plan without mutating stored embeddings.
- [ ] **Run backup-backed re-embedding**
  - **Action:** Execute:
    ```bash
    python scripts/reembed_all_faces.py --target-version facenet_vggface2
    ```
  - **Expected:** Face records are updated with the new embedding version, templates are rebuilt, and a backup snapshot is written to `uploads/migration-backups/`.
- [ ] **Rollback from migration snapshot**
  - **Action:** Execute:
    ```bash
    python scripts/reembed_all_faces.py --rollback-json uploads/migration-backups/<snapshot>.json
    ```
  - **Expected:** Stored embeddings and template metadata return to the previous version.

---

## Testing Log

| Date | Feature | Status | Notes |
|------|---------|--------|-------|
| 2026-02-12 | Auth | Pending | |
