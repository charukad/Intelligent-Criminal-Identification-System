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
# Intelligent-Criminal-Identification-System
