# Advanced Face Recognition Roadmap

## Goal
Rebuild the current prototype into a measurable, auditable, and safer face-recognition system that prefers `unknown` over wrong matches and is grounded in real evaluation data instead of guessed thresholds.

## Current Problems
- Recognition can return wrong-person matches.
- Recognition can return multiple results for a single intended subject.
- The current match threshold and confidence mapping are not calibrated to the real embedding distance distribution.
- Enrollment allows low-quality or duplicate-person data into the database.
- Operators cannot see why a result was accepted or rejected.
- The system has no benchmark pipeline for model updates or threshold changes.

## Design Principles
- Never optimize for "more matches" at the cost of wrong matches.
- Every recognition decision must be explainable.
- Enrollment quality matters as much as model quality.
- Embedding versions, thresholds, and preprocessing must be tracked.
- Debugging and evaluation tooling is a required product feature, not optional support code.

## Milestone Map

| Milestone | Focus | Outcome | Status |
|---|---|---|---|
| M0 | Diagnostics and evaluation | We can explain why a recognition result happened | Completed |
| M1 | Enrollment quality gate | Bad face data is blocked before it enters the system | Completed |
| M4 | Duplicate-person detection | Same person across multiple criminal records is flagged | In progress |
| M2 | Identity template modeling | Each criminal is represented as a stable multi-image identity profile | Completed |
| M3 | Recognition decision engine | Match decisions are calibrated and tiered | Completed |
| M5 | Frontend review and operator workflow | Operators can review, inspect, and correct recognition behavior | Completed |
| M6 | Offline benchmark and model governance | Threshold and model changes are measured before rollout | Completed |
| M7 | Model upgrade path | The system can be retrained, re-embedded, and rolled forward safely | Completed |

## Current Execution Order

This is the active implementation order and current status for the repo:

1. `M0 diagnostics and evaluation`
   Status: `Completed`
2. `M1 enrollment quality gate`
   Status: `Completed`
3. `M4 duplicate-person detection`
   Status: `In progress`
4. `M2 identity template modeling`
   Status: `Completed`
5. `M3 recognition decision engine`
   Status: `Completed`
6. `M5 frontend review workflow`
   Status: `Completed`
7. `M6 benchmark governance`
   Status: `Completed`
8. `M7 model upgrade path`
   Status: `Completed`

## M0. Diagnostics And Evaluation

### Progress
- [x] Recognition debug response with raw distances and top candidates.
- [x] Identify-page diagnostics panel for operators.
- [x] Offline embedding evaluation script for same-person vs different-person distance analysis.
- [x] Database audit script for duplicate or suspicious enrollments.
- [ ] Exportable recognition report workflow.

### Latest Findings
- Live embedding evaluation on the current database showed heavy overlap between positive and negative distances.
- Positive pair `p95` was `0.007712`, while negative pair `p05` was `0.003841`.
- The current threshold `0.01` produced `TAR=1.0` and `FAR=1.0` on the sampled live data, which means it accepts essentially everything in that dataset.
- The best sampled balanced threshold was around `0.004898`, but even that still had `FAR=0.181818`, which is too high for trustworthy identification.
- The live face-database audit flagged all `3` current criminal records across `3` suspicious criminal-pair groups.
- The closest cross-criminal face distance found was `0.003162`, which falls inside the strong duplicate-risk band.
- Conclusion: model/data quality and duplicate-record risk must be addressed before threshold tuning alone can make the system reliable.

### Deliverables
- Add a debug mode to recognition responses.
- Add offline evaluation scripts for same-person vs different-person distance analysis.
- Add a database audit script for duplicate or suspicious enrollments.
- Replace fake confidence with raw distance plus decision reason.
- Record why a result was rejected: `no_face`, `multiple_faces`, `over_threshold`, `low_quality`, `duplicate_risk`, `ambiguous`.

### Files To Add
- `backend/src/schemas/recognition.py`
- `backend/scripts/evaluate_embeddings.py`
- `backend/scripts/audit_face_database.py`
- `backend/scripts/export_recognition_report.py`
- `frontend/src/components/recognition/RecognitionDebugPanel.tsx`
- `frontend/src/types/recognition.ts`

### Files To Change
- `backend/src/api/v1/endpoints/recognition.py`
- `backend/src/services/recognition_service.py`
- `backend/src/infrastructure/repositories/face.py`
- `backend/tests/test_recognition_service.py`
- `frontend/src/api/recognition.ts`
- `frontend/src/pages/Identify.tsx`

### Acceptance Criteria
- A recognition request can optionally return top candidate criminals with raw distances.
- Operators can see which detected face box was actually used.
- We can generate a report showing positive and negative pair distance distributions.
- We can list suspicious records whose embeddings are too close across different criminals.

## M1. Enrollment Quality Gate

### Progress
- [x] Backend face quality assessment for blur, brightness, and face size.
- [x] Enrollment now rejects low-quality images before embeddings are stored.
- [x] Stored face records now include quality metadata and warnings.
- [x] Frontend quality warnings and badges during upload.
- [x] Landmark-based face alignment before embedding generation.
- [x] Landmark-based pose and feature-occlusion checks during preview and enrollment.

### Deliverables
- Add blur, brightness, face-size, occlusion, and multi-face checks before saving embeddings.
- Add consistent face alignment before embedding generation.
- Add enrollment warnings and hard rejects in both backend and frontend.
- Store quality metadata per enrolled face image.

### Files To Add
- `backend/src/services/ai/face_quality.py`
- `backend/src/services/ai/face_alignment.py`
- `backend/src/services/face_quality_service.py`
- `backend/src/schemas/face_quality.py`
- `backend/migrations/versions/<timestamp>_add_face_quality_columns.py`
- `frontend/src/components/criminals/FaceQualityBadge.tsx`
- `frontend/src/components/criminals/FaceQualityWarnings.tsx`

### Files To Change
- `backend/src/services/face_enrollment_service.py`
- `backend/src/services/ai/pipeline.py`
- `backend/src/services/ai/strategies.py`
- `backend/src/domain/models/face.py`
- `backend/src/api/v1/endpoints/criminals.py`
- `backend/tests/test_face_enrollment.py`
- `frontend/src/components/criminals/FaceEnrollmentPicker.tsx`
- `frontend/src/components/criminals/CriminalDialog.tsx`
- `frontend/src/pages/Criminals.tsx`

### Acceptance Criteria
- Enrollment rejects unusable images before embeddings are stored.
- Stored face records include quality metadata and rejection reasons.
- Frontend clearly shows why an image cannot be enrolled.
- Enrolled and identified faces are aligned consistently before TraceNet embedding generation.
- Side-angle and feature-obscured faces are flagged before embeddings are stored.

## M2. Identity Template Modeling

### Progress
- [x] Added an `identity_templates` table with pgvector embeddings and criminal-level membership metadata.
- [x] Rebuild criminal templates automatically when faces are enrolled, deleted, or marked primary.
- [x] Recognition now ranks criminal identity templates instead of raw face rows.
- [x] Face records now track template roles: `primary`, `support`, `archived`, `outlier`.

### Deliverables
- Move from per-image-only lookup to criminal-level identity templates.
- Add aggregate template generation from multiple enrolled embeddings.
- Track primary, support, archived, and outlier embeddings per criminal.
- Add re-template generation when new faces are added or removed.

### Files To Add
- `backend/src/domain/models/identity_template.py`
- `backend/src/infrastructure/repositories/identity_template.py`
- `backend/src/services/identity_template_service.py`
- `backend/src/schemas/identity_template.py`
- `backend/migrations/versions/<timestamp>_add_identity_templates.py`

### Files To Change
- `backend/src/domain/models/__init__.py`
- `backend/src/domain/models/criminal.py`
- `backend/src/domain/models/face.py`
- `backend/src/services/face_enrollment_service.py`
- `backend/src/services/recognition_service.py`
- `backend/src/api/v1/endpoints/criminals.py`
- `backend/tests/test_face_enrollment.py`
- `backend/tests/test_recognition_service.py`

### Acceptance Criteria
- Each criminal has a generated identity template or template set.
- Recognition can score against a criminal identity, not only one stored face row.
- Outlier enrolled images can be flagged and excluded from template generation.

## M3. Recognition Decision Engine

### Progress
- [x] Added a recognition policy service with `match`, `possible_match`, and `unknown` outcomes.
- [x] Added template-candidate reranking before final decision evaluation.
- [x] Added explicit scene mode versus single-face mode in the recognition API.
- [x] Updated the Identify page and diagnostics UI for tiered decisions and template metadata.
- [x] Extended the evaluator with holdout template calibration and generated a live policy report from the Docker database.
- [x] Replaced hand-set decision defaults with measured template-level thresholds and separation margins.

### Deliverables
- Replace current single nearest-neighbor rule with calibrated decision bands.
- Add three outcomes: `match`, `possible_match`, `unknown`.
- Add top-k criminal aggregation instead of raw top-k face rows.
- Add scene mode and single-face mode as separate paths.

### Files To Add
- `backend/src/services/recognition_policy_service.py`
- `backend/src/services/candidate_reranker.py`
- `backend/src/schemas/recognition_policy.py`

### Files To Change
- `backend/src/services/recognition_service.py`
- `backend/src/infrastructure/repositories/face.py`
- `backend/src/api/v1/endpoints/recognition.py`
- `backend/scripts/evaluate_embeddings.py`
- `backend/tests/test_recognition_service.py`
- `backend/tests/test_evaluate_embeddings.py`
- `frontend/src/api/recognition.ts`
- `frontend/src/pages/Identify.tsx`

### Acceptance Criteria
- Recognition responses include decision tier and decision reason.
- Weak candidates become `possible_match` or `unknown`, not forced `match`.
- Single-face uploads default to one analyzed subject.
- Scene mode clearly separates multiple detected people.
- Match and possible-match defaults come from measured template calibration, not guessed constants.

## M4. Duplicate-Person Detection

### Progress
- [x] Added a backend duplicate-identity service that screens new face enrollments against other criminal identity templates.
- [x] Added a persistent review queue for duplicate-identity conflicts.
- [x] Probable duplicate enrollments are blocked with a `409` response and an attached review-case ID.
- [x] Lower-confidence duplicate risks are accepted with a stored review case for operator follow-up.
- [x] Added backend endpoints to list and resolve duplicate review cases.
- [x] Added operator-triggered criminal merge workflow from duplicate review cases, including linked-record reassignment.

### Deliverables
- Detect likely duplicate identities across different criminal records.
- Warn or block enrollment when a new image is too close to a different criminal.
- Add a manual review queue for suspected duplicate records.

### Files To Add
- `backend/src/services/duplicate_identity_service.py`
- `backend/src/domain/models/review_case.py`
- `backend/src/infrastructure/repositories/review_case.py`
- `backend/src/schemas/review_case.py`
- `backend/migrations/versions/<timestamp>_add_review_queue.py`
- `frontend/src/pages/ReviewQueue.tsx`
- `frontend/src/components/review/DuplicateIdentityReviewCard.tsx`

### Files To Change
- `backend/src/services/face_enrollment_service.py`
- `backend/src/api/v1/endpoints/criminals.py`
- `backend/src/api/v1/api.py`
- `backend/tests/test_face_enrollment.py`
- `frontend/src/App.tsx`
- `frontend/src/components/layout/DashboardLayout.tsx`

### Acceptance Criteria
- New enrollment can flag likely duplicate-person conflicts across records.
- Duplicate-review items can be listed and resolved by an operator.
- We can export a list of likely duplicate criminal identities.

## M5. Frontend Review And Operator Workflow

### Progress
- [x] Detection-box overlay on the Identify page.
- [x] Structured candidate review table with raw distances and direct profile links.
- [x] Criminal face timeline now shows template membership and outlier status without database inspection.
- [x] Added explicit operator actions for "mark enrollment as bad" and "recompute template" on the criminal face timeline.
- [x] Added an explicit "merge review needed" escalation action from the recognition review UI.

### Deliverables
- Show detection boxes on the Identify page.
- Show top candidate list with raw distances and reject reason.
- Show face quality and template membership on criminal face timeline.
- Add explicit operator actions for "mark enrollment as bad", "merge review needed", and "recompute template".

### Files To Add
- `frontend/src/components/recognition/RecognitionOverlay.tsx`
- `frontend/src/components/recognition/RecognitionCandidateTable.tsx`
- `frontend/src/components/criminals/FaceTemplateSummary.tsx`
- `frontend/src/components/criminals/FaceOutlierWarning.tsx`

### Files To Change
- `frontend/src/pages/Identify.tsx`
- `frontend/src/pages/Criminals.tsx`
- `frontend/src/api/recognition.ts`
- `frontend/src/api/criminals.ts`
- `frontend/src/types/criminal.ts`
- `frontend/src/types/recognition.ts`

### Acceptance Criteria
- Operators can see exactly what face region was analyzed.
- Operators can see why a match was rejected.
- Operators can inspect enrolled images and outliers without going to the database.

## M6. Offline Benchmark And Model Governance

### Progress
- [x] Added a repeatable benchmark-manifest builder for identity-labelled image folders.
- [x] Added an offline benchmark runner that produces pair metrics and template calibration from a manifest.
- [x] Added a threshold governance report with a go/conditional/no-go decision and release checklist.
- [x] Added benchmark dataset-format documentation for local fixtures.
- [x] Updated repo documentation with the benchmark workflow and rollout expectations.
- [x] Added a release-gate script that fails when the threshold governance report is stale, mismatched, or not approved.

### Deliverables
- Add repeatable evaluation datasets and scripts.
- Store benchmark outputs for each embedding version.
- Add threshold recommendation generation from real pair distributions.
- Create a go/no-go checklist before any model rollout.

### Files To Add
- `backend/scripts/build_pair_benchmark.py`
- `backend/scripts/run_recognition_benchmark.py`
- `backend/scripts/generate_threshold_report.py`
- `backend/tests/fixtures/benchmark/README.md`
- `TESTING_PLAN.md` additions for benchmark workflow

### Files To Change
- `README.md`
- `TESTING_PLAN.md`
- `project_overview.md`

### Acceptance Criteria
- A benchmark run produces FAR, FRR, TAR, precision, recall, ROC-style outputs, and recommended thresholds.
- Threshold changes are documented and reproducible.
- Model releases cannot proceed without benchmark evidence.

## M7. Model Upgrade Path

### Progress
- [x] Added a model-version registry for supported embedders and runtime selection through `FACE_EMBEDDING_VERSION`.
- [x] Added offline model-comparison tooling to benchmark multiple embedders on the same held-out manifest.
- [x] Added embedding migration metadata to face records and a migration file for persistence.
- [x] Added a snapshot-based re-embedding and rollback service with CLI entry points.
- [x] Generated a real comparison report on the held-out `Face 2` dataset.
- [x] Run the live database migration against the active Docker deployment.
- [x] Validate the rollback snapshot in dry-run mode against the active Docker deployment.
- [x] Complete a full live rollback-and-restore drill against the active Docker deployment.

### Latest Findings
- Real model comparison on the `face-2-heldout` benchmark showed a decisive difference between the current custom model and the stronger baseline.
- `tracenet_v1` received a `no_go` decision with own-template top-1 rate `0.306122`.
- `facenet_vggface2` received a `go` decision with own-template top-1 rate `1.0` and match FAR `0.006667`.
- Docker runtime selection is now configured to prefer `facenet_vggface2` by default through `FACE_EMBEDDING_VERSION`.
- The live Docker migration is complete: `10` face embeddings were re-embedded to `facenet_vggface2`, `3` identity templates were rebuilt, and post-migration dry runs show `0` remaining eligible faces.
- Rollback readiness is in place through snapshot `/app/uploads/migration-backups/facenet_vggface2-20260304-083052.json`, which validated successfully in dry-run mode.
- A full live rollback-and-restore drill is now complete:
  rollback to `tracenet_v1` from snapshot, runtime switch to `tracenet_v1`, then restore back to `facenet_vggface2` with a fresh backup snapshot `/app/uploads/migration-backups/facenet_vggface2-20260304-201810.json`.

### Deliverables
- Compare TraceNet against stronger face-embedding baselines.
- Add embedding version migration support.
- Add a safe re-embedding pipeline for all stored face records.
- Add rollback support for model changes.

### Files To Add
- `backend/scripts/reembed_all_faces.py`
- `backend/scripts/compare_models.py`
- `backend/src/services/embedding_migration_service.py`
- `backend/src/schemas/model_version.py`
- `backend/migrations/versions/<timestamp>_add_embedding_version_metadata.py`

### Files To Change
- `backend/src/services/ai/strategies.py`
- `backend/src/services/face_enrollment_service.py`
- `backend/src/services/recognition_service.py`
- `backend/src/domain/models/face.py`
- `backend/tests/test_face_enrollment.py`
- `backend/tests/test_recognition_service.py`

### Acceptance Criteria
- We can re-embed all stored faces with a new model version.
- We can compare old and new model performance before switching.
- We can roll back recognition to an earlier embedding version if needed.

## Recommended Build Order
1. M0 diagnostics and evaluation
2. M1 enrollment quality gate
3. M4 duplicate-person detection
4. M2 identity template modeling
5. M3 recognition decision engine
6. M5 frontend review workflow
7. M6 benchmark governance
8. M7 model upgrade path

## Immediate First Sprint

### Sprint Goal
Get the system out of "blind guessing" mode and into "measurable and explainable" mode.

### First Sprint Deliverables
- Recognition debug response with top candidates and raw distances
- Identify page debug panel with selected face box and top candidate list
- Database audit script for suspicious duplicate-person embeddings
- Offline evaluation script for positive/negative distance distributions

### First Sprint Files
- Add `backend/src/schemas/recognition.py`
- Add `backend/scripts/evaluate_embeddings.py`
- Add `backend/scripts/audit_face_database.py`
- Change `backend/src/services/recognition_service.py`
- Change `backend/src/api/v1/endpoints/recognition.py`
- Change `backend/src/infrastructure/repositories/face.py`
- Change `backend/tests/test_recognition_service.py`
- Add `frontend/src/components/recognition/RecognitionDebugPanel.tsx`
- Add `frontend/src/types/recognition.ts`
- Change `frontend/src/api/recognition.ts`
- Change `frontend/src/pages/Identify.tsx`

## Success Definition
- Known-person images match the correct criminal with a calibrated threshold.
- Unknown people are rejected instead of being forced into a wrong identity.
- Duplicate or suspicious enrollments are visible and reviewable.
- Every recognition decision can be explained from stored evidence.
- Model or threshold changes are backed by benchmark results, not intuition.
