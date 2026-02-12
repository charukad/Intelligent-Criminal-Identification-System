# TraceIQ: Intelligent Criminal Identification System
## Comprehensive Technical Specification & Project Overview

**Document Version:** 2.0.0
**Date:** 2026-02-05
**Status:** DRAFT - Detailed Specification

---

# 1. Introduction

## 1.1 Document Purpose
The purpose of this document is to provide a comprehensive, granular, and exhaustive specification for the "TraceIQ" Intelligent Criminal Identification System. This document serves as the single source of truth for all stakeholders, developers, project managers, and quality assurance personnel. It details the functional requirements, non-functional attributes, system architecture, database schema, API specifications, and security protocols required to build a production-grade system for law enforcement agencies in Sri Lanka.

## 1.2 Project Scope
TraceIQ is a dual-platform solution (Web & Mobile) designed to unify criminal record management and facilitate real-time identification.
**In Scope:**
*   **Centralized Criminal Database:** A cloud-based (or on-premise) repository of criminal profiles.
*   **Facial Recognition Engine:** A deep-learning-based service for identifying individuals from images.
*   **Web Command Dashboard:** A React-based interface for data entry, case management, and analytics.
*   **Mobile Field Unit:** A Flutter-based mobile application for on-the-spot identification and alert reception.
*   **Offline Synchronization:** Capabilities for mobile devices to operate in low-connectivity zones.
*   **Audit Logging:** Immutable logs of all system interactions.

**Out of Scope:**
*   Hardware procurement (assumes officers use existing Department-issued phones or personal devices).
*   Forensic DNA analysis features.
*   Integration with international databases (Interpol) *in Phase 1*.

## 1.3 Definitions, Acronyms, and Abbreviations
| Term | Definition |
| :--- | :--- |
| **P1, P2, P3** | Priority Levels (Critical, High, Medium) |
| **FR** | Facial Recognition |
| **IO** | Investigating Officer |
| **OIC** | Officer In-Charge |
| **MFA** | Multi-Factor Authentication |
| **JWT** | JSON Web Token |
| **CRUD** | Create, Read, Update, Delete |
| **REST** | Representational State Transfer |
| **POI** | Person of Interest |
| **TLS** | Transport Layer Security |
| **AES** | Advanced Encryption Standard |
| **UUID** | Universally Unique Identifier |

---

# 2. Detailed Stakeholder & User Analysis

## 2.1 User Personas

### 2.1.1 The System Administrator (Admin)
*   **Profile:** A technical officer or IT specialist within the Police Department.
*   **Goals:** Ensure 99.9% system uptime, manage user roles, secure data, and perform backups.
*   **Pain Points:** Fear of data breaches, managing forgotten passwords, slow system performance.
*   **Key Responsibilities:**
    *   Provisioning accounts for new officers.
    *   Revoking access for retired/suspended officers.
    *   Configuring system-wide thresholds for Facial Recognition confidence.
    *   Viewing system health logs.

### 2.1.2 The Senior Investigating Officer (SIO) / OIC
*   **Profile:** High-ranking officer handling major crimes or station command.
*   **Goals:** Solve cases quickly, link evidence across cases, generate accurate reports for court.
*   **Pain Points:** Missing files, lack of "big picture" data, inability to track repeat offenders across districts.
*   **Key Responsibilities:**
    *   Validating high-profile criminal records.
    *   Assigning cases to field officers.
    *   Reviewing "High Confidence" facial matches.
    *   Generating statistical crime reports.

### 2.1.3 The Field Officer (Patrol Unit)
*   **Profile:** Constable or Sergeant on traffic duty, patrol, or raid operations.
*   **Goals:** Instant verification of suspects, personal safety, quick reporting.
*   **Pain Points:** Slow verification (phone calls), dead zones (no signal), dangerous suspects with unknown history.
*   **Key Responsibilities:**
    *   Scanning faces during routine stops.
    *   Checking "Wanted" lists.
    *   Receiving "APB" (All Points Bulletin) alerts.

### 2.1.4 The Data Entry Operator / Clerk
*   **Profile:** Civil staff or desk officer responsible for digitization.
*   **Goals:** Fast data entry, accuracy, minimal system lag.
*   **Pain Points:** Repetitive forms, confusing UI, upload failures.
*   **Key Responsibilities:**
    *   Digitizing physical "Crime Books".
    *   Uploading mugshots from varying sources.

---

# 3. Comprehensive Functional Requirements

## 3.1 Module: Authentication & Authorization (AuthSys)

### [FR-AUTH-001] Secure Login
*   **Description:** Users must authenticate using a username/email and a complex password.
*   **Inputs:** Username (String), Password (String, masked).
*   **Validation:**
    *   Username must be alphanumeric.
    *   Password must be >10 characters, include 1 uppercase, 1 lowercase, 1 number, 1 special char.
*   **Process:**
    1.  User submits credentials.
    2.  System hashes password (Argon2id).
    3.  System verifies hash against DB.
    4.  If valid, issue Access Token (JWT, 15 min expiry) and Refresh Token (HTTP-only cookie, 7 day expiry).
*   **Error Handling:**
    *   3 failed attempts -> CAPTCHA challenge.
    *   5 failed attempts -> 15-minute account lockout.

### [FR-AUTH-002] Multi-Factor Authentication (MFA)
*   **Description:** Critical roles (Admin, SIO) must use MFA.
*   **Mechanism:** Time-based One-Time Password (TOTP) via Google Authenticator or SMS OTP.
*   **Trigger:** Upon successful password verification for designated roles.

### [FR-AUTH-003] Session Management
*   **Description:** Auto-logout functionality.
*   **Timeout:** 30 minutes of inactivity.
*   **Warning:** Display modal warning at 28 minutes.

## 3.2 Module: Facial Recognition (FaceEngine)

### [FR-CORE-001] Image Ingestion & Pre-processing
*   **Description:** System accepts individual or bulk image uploads.
*   **Formats:** JPEG, PNG, WEBP, BMP.
*   **Max Size:** 10MB per image.
*   **Preprocessing Steps:**
    1.  **Format Validation:** Check magic bytes.
    2.  **EXIF Stripping:** Remove GPS/Camera metadata (privacy/security).
    3.  **Face Detection:** Use MTCNN or RetinaFace to locate face landmarks.
    4.  **Alignment:** Rotate/Scale image so eyes are horizontally aligned.
    5.  **Cropping:** Crop to face region + 20% margin.
    6.  **normalization:** Adjust brightness/contrast (Histogram Equalization).

### [FR-CORE-002] Embedding Generation
*   **Description:** Convert processed face image to a vector representation.
*   **Model:** Inception ResNet V1 (trained on VGGFace2 or CASIA-WebFace).
*   **Output:** 512-dimensional float array (vector).
*   **Latency:** < 200ms per image on GPU.

### [FR-CORE-003] 1:N Identification Search
*   **Description:** Compare a query vector against the entire database of criminal embedding vectors.
*   **Algorithm:** Approximate Nearest Neighbor (ANN) using HNSW (Hierarchical Navigable Small World) graphs or Faiss.
*   **Distance Metric:** Cosine Similarity or Euclidean Distance.
*   **parameters:**
    *   `threshold`: 0.6 (tunable).
    *   `limit`: Top 10 results.
*   **Response:** List of candidates with `confidence_score` and `criminal_id`.

## 3.3 Module: Criminal Record Management (CRM)

### [FR-CRM-001] Criminal Profile Creation
*   **Form Fields:**
    *   **NIC (National Identity Card):** Unique Constraint. Pattern `[0-9]{9}[VvXx] | [0-9]{12}`.
    *   **Full Name:** Required.
    *   **Aliases:** List of strings.
    *   **Date of Birth:** Date picker.
    *   **Gender:** Enum (Male, Female, Other).
    *   **Scanning:** Support scanning NIC barcode (future scope, field exists).
    *   **Physical Features:**
        *   Height (cm).
        *   Weight (kg).
        *   Hair Color (Enum).
        *   Eye Color (Enum).
        *   Skin Tone (Enum).
        *   Distinguishing Marks (Text Area + Tagging e.g., "Tattoo-Left-Arm", "Scar-Right-Cheek").

### [FR-CRM-002] Offense History Tracking
*   **Relation:** One-to-Many (One Criminal -> Many Offenses).
*   **Data Points per Offense:**
    *   `Case_ID`: Link to Case Module.
    *   `Offense_Type`: Enum (Robbery, Homicide, Narcotics, etc.).
    *   `Date_of_Incident`: Datetime.
    *   `Role`: Enum (Principal, Accomplice, Mastermind).
    *   `Status`: Enum (Suspect, Charged, Convicted, Acquitted).
    *   `Sentence_Details`: Text (e.g., "5 years RI").

## 3.4 Module: Case Management & Link Analysis (CMS)

### [FR-CMS-001] Digital Case Files
*   **Structure:**
    *   `Case_Number`: Auto-generated format `YYYY-STATION-SEQ` (e.g., `2024-COL-00452`).
    *   `OIC_Assigned`: User ID.
    *   `Date_Opened`: Timestamp.
    *   `Status`: Open, Closed, Cold, Suspended.
    *   `Description`: Rich Text.

### [FR-CMS-002] Suspect Linking
*   **Function:** Link profiles from CRM to a Case.
*   **Metadata:** Add notes specific to the suspect in *this* case (e.g., "Was wearing a red cap").

---

# 4. Detailed System Architecture

## 4.1 High-Level Diagram
`Mobile App / Web App` <--> `Load Balancer` <--> `API Gateway` <--> `Application Server` <--> `Database Cluster`

## 4.2 Backend Layer Specifications
*   **Language:** Python 3.11+
*   **Framework:** FastAPI (for high-performance async execution).
*   **Runtime:** Uvicorn (ASGI server).
*   **Containerization:** Docker (Alpine Linux base images).

## 4.3 Database Schema Design (Relational - PostgreSQL)

### Table: `users`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | PK, Default: gen_random_uuid() | Internal ID |
| `username` | VARCHAR(50) | Unique, Not Null | Login handle |
| `email` | VARCHAR(255)| Unique, Not Null | Contact email |
| `password_hash`| VARCHAR(255)| Not Null | Argon2 Hash |
| `role` | VARCHAR(20) | Enum: ADMIN, SIO, FO, VIEWER | Access Level |
| `badgev_number`| VARCHAR(20) | Unique | Police ID |
| `station_id` | UUID | FK -> stations.id | Duty Station |
| `is_active` | BOOLEAN | Default: True | Soft delete flag |
| `created_at` | TIMESTAMPTZ | Default: NOW() | Audit |

### Table: `criminals`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | PK | Internal ID |
| `nic` | VARCHAR(20) | Unique, Nullable | National ID |
| `first_name` | VARCHAR(100)| Not Null | |
| `last_name` | VARCHAR(100)| Not Null | |
| `dob` | DATE | | Date of Birth |
| `blood_type` | VARCHAR(5) | | Medical info |
| `last_known_address`| TEXT | | |
| `status` | VARCHAR(20) | Enum: WANTED, IN_CUSTODY, ...| |
| `threat_level` | INT | 1-5 | 5 = Extreme Danger |

### Table: `facial_embeddings`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | PK | |
| `criminal_id` | UUID | FK -> criminals.id | Owner of face |
| `embedding` | VECTOR(512)| | pgvector data type |
| `image_url` | TEXT | | Path to object storage |
| `is_primary` | BOOLEAN | | Is this the main mugshot? |

### Table: `cases`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | PK | |
| `case_number` | VARCHAR(50) | Unique | Official File No |
| `title` | VARCHAR(255)| Not Null | |
| `description` | TEXT | | |
| `station_id` | UUID | FK -> stations.id | |
| `lead_officer_id`| UUID | FK -> users.id | |

## 4.4 Mobile App Architecture
*   **Framework:** Flutter (Dart).
*   **State Management:** BLoC or Riverpod.
*   **Local Database:** SQLite (via Drift or Sqflite packages).
*   **Sync Logic:**
    *   Pull "Delta" (changes) every 1 hour.
    *   Push "Offline Logs/Drafts" immediately when online.

---

# 5. API Specification (Endpoints)

## 5.1 Authentication Group `/api/v1/auth`
*   `POST /login`:
    *   **Body:** `{"username": "...", "password": "..."}`
    *   **200 OK:** `{"access_token": "...", "user": {...}}`
    *   **401 Unauthorized:** Invalid creds.
*   `POST /refresh`:
    *   **Body:** (Cookie: refresh_token)
    *   **200 OK:** New access token.

## 5.2 Criminals Group `/api/v1/criminals`
*   `POST /`: Create new profile. Requires `CRM_WRITE` permission.
*   `GET /{id}`: Get full profile details including Offense History payload.
*   `PUT /{id}`: Update specific fields.
*   `POST /{id}/photos`: Upload new mugshot. Triggers async vector embedding job.

## 5.3 Recognition Group `/api/v1/recognize`
*   `POST /identify`:
    *   **Body:** `multipart/form-data` (image file).
    *   **Process:**
        1.  Validate file.
        2.  Run face detection.
        3.  Generate embedding.
        4.  Query Vector DB.
    *   **Response:**
        ```json
        {
          "matches": [
            {
              "criminal_id": "uuid...",
              "name": "Kamal Perera",
              "confidence": 0.98,
              "thumbnail_url": "..."
            },
            ...
          ],
          "processing_time_ms": 145
        }
        ```

---

# 6. User Interface Design Guidelines

## 6.1 Design Principles
1.  **High Contrast:** Use dark mode by default for Operations Centers (reduces eye strain). Mobile app should have "Day/Night" modes.
2.  **Clear Typography:** Inter or Roboto font. Minimum size 14px for body text.
3.  **Color Coding:**
    *   **Red:** Danger, Wanted, High Threat.
    *   **Orange:** Caution, Missing Info.
    *   **Green:** Verified, Safe, Low Threat.
    *   **Blue:** Informational, Links.

## 6.2 Key Screen Specifications

### 6.2.1 Dashboard (Web)
*   **Header:** Global Search Bar, User Profile, Notification Bell.
*   **Sidebar:** Navigation (Home, Criminals, Cases, Reports, Settings).
*   **Main Area:**
    *   "Recent Alerts" Widget (Live feed of system hits).
    *   "Stats" Widget (Crimes this week, Arrests made).
    *   "Map View" (Heatmap of activity).

### 6.2.2 Mobile Identification Screen
*   **Viewfinder:** Full screen camera view.
*   **Overlay:** "Scanning..." animation.
*   **Result Card (Bottom Sheet):**
    *   Slides up when match found.
    *   Shows: Photo, Name, NIC, "WANTED" badge (if applicable).
    *   Actions: "View Full Profile", "Report Sighting", "False Positive".

---

# 7. Non-Functional Requirements & constraints

## 7.1 Performance
*   **API Response:** < 200ms for data queries. < 2 seconds for Facial Recognition.
*   **Throughput:** Support 10 concurrent requests per second (initial scale).
*   **Database:** Queries must use indexes. No full table scans on `criminals` table.

## 7.2 Security
*   **Data at Rest:** All sensitive columns (NIC, Name) encrypted.
*   **Data in Transit:** Force HTTPS. HSTS enabled.
*   **Input Sanitization:** Prevent SQL Injection and XSS using ORM and framework validators.
*   **Rate Limiting:** Global limit of 100 requests/min per IP to prevent DDoS.

## 7.3 Compatibility
*   **Web:** Chrome 90+, Firefox 88+, Edge (Chromium).
*   **Mobile:** Android 10+, iOS 14+.

---

# 8. Testing Strategy

## 8.1 Unit Testing
*   **Backend:** Pytest. Coverage > 90%. Mock all DB and External calls.
*   **Frontend:** Jest + React Testing Library. Test validation logic and rendering.

## 8.2 Integration Testing
*   Test flow: `Create Profile` -> `Upload Photo` -> `Search Photo` -> `Verify Match`.
*   Verify Database triggers and Constraints.

## 8.3 User Acceptance Testing (UAT)
*   Deploy to Staging environment.
*   Select group of 5 real officers to perform "Day in the Life" scripts.

---

# 9. Deployment & DevOps

## 9.1 CI/CD Pipeline (GitHub Actions)
1.  **Push code:** Trigger pipeline.
2.  **Lint:** Run `ruff` (Python) and `eslint` (JS).
3.  **Test:** Run unit tests.
4.  **Build:** Build Docker images.
5.  **Deploy (Dev):** updates dev server automatically.

## 9.2 Infrastructure (AWS Example)
*   **EC2:** Hosting the Docker containers (API + Celery Workers).
*   **RDS (PostgreSQL):** Managed Database service.
*   **S3:** Storing high-res mugshots.
*   **ElastiCache (Redis):** Caching sessions and frequent queries.

---

# 10. Future Roadmap (Post-MVP)

1.  **Video Analytics:** Real-time CCTV feed processing.
2.  **Public Portal:** Allow citizens to submit anonymous tips.
3.  **ALPR:** Automatic License Plate Recognition integration.
4.  **Voice Biometrics:** Voice print identification.
5.  **Blockchain:** For immutable evidence logging (chain of custody).

---

*(End of Specification Document)*
