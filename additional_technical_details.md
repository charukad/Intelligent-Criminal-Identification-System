# TraceIQ: Additional Technical Specifications & Visual Architecture
## Diagrams, Schemas, and Configuration Standards

**Document Version:** 1.0.0
**Date:** 2026-02-05
**Reference:** Supplements `project_overview.md` and `ai_architecture.md`

---

# 1. Visual System Architecture

## 1.1 High-Level Deployment Diagram
This diagram illustrates how the components interacts within the cloud/on-premise infrastructure.

```mermaid
graph TD
    subgraph Client Layer
        Mobile[Mobile App (Flutter)] -->|HTTPS/REST| APIGateway
        Web[Web Dashboard (React)] -->|HTTPS/REST| APIGateway
    end

    subgraph "DMZ / API Layer"
        APIGateway[Nginx / Load Balancer] --> API_Svc
    end

    subgraph "Application Layer (Docker Network)"
        API_Svc[Backend API (FastAPI)]
        Celery[Celery Workers (Async Tasks)]
        AI_Svc[AI Engine (PyTorch/FaceNet)]
    end

    subgraph "Data Persistence Layer"
        DB_SQL[(PostgreSQL - User/Case Data)]
        DB_Vec[(Vector Store / PGVector)]
        Redis[(Redis - Cache/Queue)]
        ObjStore[(S3/MinIO - Image Storage)]
    end

    API_Svc --> DB_SQL
    API_Svc --> Redis
    API_Svc --> ObjStore
    API_Svc -->|Task Queue| Celery
    Celery -->|Process Images| AI_Svc
    AI_Svc --> DB_Vec
```

## 1.2 Core Data Flow (Face Identification)

```mermaid
sequenceDiagram
    participant Officer as Field Officer (Mobile)
    participant API as Backend API
    participant AI as AI Engine
    participant VDB as Vector DB
    participant SQL as SQL DB

    Officer->>Officer: Captures Photo
    Officer->>API: POST /identify (image)
    activate API
    API->>AI: Send Image for Processing
    activate AI
    AI->>AI: Detect Face -> Align -> Embed
    AI->>VDB: Query Nearest Neighbors (k=10)
    activate VDB
    VDB-->>AI: Return Candidate IDs & Scores
    deactivate VDB
    AI-->>API: Return Search Results
    deactivate AI
    
    loop Enrich Data
        API->>SQL: Get Criminal Details (Name, Status) for IDs
        SQL-->>API: Return Profile Data
    end

    API-->>Officer: Return Enriched Match List
    deactivate API
    Officer->>Officer: Review & Verify
```

---

# 2. Entity Relationship (ER) Diagram

This diagram visualizes the PostgreSQL database schema outlined in the Project Overview.

```mermaid
erDiagram
    USERS ||--o{ CASES : manages
    USERS ||--o{ AUDIT_LOGS : generates
    STATIONS ||--|{ USERS : employs
    STATIONS ||--o{ CASES : handles
    
    CRIMINALS ||--o{ OFFENSES : committed
    CRIMINALS ||--o{ PHOTOS : has
    CRIMINALS ||--o| FACE_EMBEDDINGS : mapped_to
    
    CASES ||--|{ CASE_SUSPECTS : involves
    CRIMINALS ||--|{ CASE_SUSPECTS : is_suspect_in

    STATIONS {
        uuid id PK
        string name
        string district
        string province
    }

    USERS {
        uuid id PK
        string username
        string role "ADMIN, SIO, FIELD_OFFICER"
        uuid station_id FK
    }

    CRIMINALS {
        uuid id PK
        string nic "Unique Index"
        string full_name
        date dob
        string threat_level "1-5"
        string status "WANTED, CUSTODY, FREE"
    }

    FACE_EMBEDDINGS {
        uuid id PK
        uuid criminal_id FK
        vector embedding "512-dim"
        string algorithm_version
    }

    OFFENSES {
        uuid id PK
        uuid criminal_id FK
        uuid case_id FK
        string offense_type
        date date_committed
        string verdict
    }

    CASES {
        uuid id PK
        string case_number
        text description
        string status
    }
```

---

# 3. Missing Technical Details & Standards

## 3.1 Environment Configuration (`.env`)
The system requires the following environment variables to run. A `.env.example` will be provided.

```bash
# App Configuration
APP_ENV=development # development, production
APP_NAME=TraceIQ
SECRET_KEY=change_this_to_a_secure_random_string
ALGORITHM=HS256

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/traceiq_db
TEST_DATABASE_URL=postgresql://user:password@localhost:5432/traceiq_test

# Redis
REDIS_URL=redis://localhost:6379/0

# Object Storage (S3 Compatible)
S3_ENDPOINT=https://s3.amazonaws.com
S3_ACCESS_KEY=xxx
S3_SECRET_KEY=xxx
S3_BUCKET_NAME=traceiq-images

# AI Engine
FACE_MODEL_PATH=./models/20180402-114759.pb
MIN_CONFIDENCE_THRESHOLD=0.65
```

## 3.2 Standard API Response Wrapper
All API responses will follow this uniform JSON structure to ensure easier parsing by Mobile/Web clients.

**Success Response (200 OK):**
```json
{
  "status": "success",
  "data": {
    "user_id": "12345",
    "name": "Officer Perera"
  },
  "meta": {
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 150
    }
  }
}
```

**Error Response (4xx/5xx):**
```json
{
  "status": "error",
  "error": {
    "code": "AUTH_001",
    "message": "Invalid credentials provided.",
    "details": "Password does not match hash."
  }
}
```

## 3.3 Error Code Registry
| Code | HTTP | Description |
| :--- | :--- | :--- |
| `GEN_001` | 500 | Internal Server Error (Unhandled Exception) |
| `AUTH_001`| 401 | Invalid Credentials |
| `AUTH_002`| 403 | Insufficient Permissions (RBAC) |
| `RES_004` | 404 | Resource Not Found |
| `VAL_001` | 422 | Validation Error (Input schema mismatch) |
| `AI_001` | 400 | No face detected in image |
| `AI_002` | 400 | Multiple faces detected (if single-mode enforced) |

---

# 4. Infrastructure & Deployment Specs

## 4.1 Docker Network Structure
To isolate services, we define a custom bridge network `traceiq-net`.
*   `proxy` (Nginx) -> Exposed on Port 80/443.
*   `backend` -> Internal Port 8000.
*   `db` -> Internal Port 5432.
*   `redis` -> Internal Port 6379.

## 4.2 Backup Strategy
*   **Database:** `pg_dump` runs nightly via Cron job. Uploaded to S3 `backups/sql/`.
*   **Images:** S3 replication enabled to a secondary region.

---
