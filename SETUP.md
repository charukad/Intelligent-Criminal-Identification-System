# TraceIQ - Setup & Installation Guide

A comprehensive facial recognition and criminal database management system for Sri Lankan law enforcement.

---

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Detailed Installation](#detailed-installation)
  - [1. Clone the Repository](#1-clone-the-repository)
  - [2. Backend Setup](#2-backend-setup)
  - [3. Database Setup](#3-database-setup)
  - [4. Frontend Setup](#4-frontend-setup)
- [Running the Application](#running-the-application)
- [Docker Deployment](#docker-deployment)
- [Troubleshooting](#troubleshooting)
- [Testing](#testing)

---

## Prerequisites

Before you begin, ensure you have the following installed on your system:

### Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| **Python** | 3.10+ | Backend runtime |
| **Node.js** | 18+ | Frontend runtime |
| **npm** | 9+ | Frontend package manager |
| **PostgreSQL** | 14+ | Database |
| **Git** | Latest | Version control |

### Optional (Recommended)

- **Docker** & **Docker Compose** - For containerized deployment
- **PostgreSQL GUI** (pgAdmin, DBeaver) - For database management

### System Requirements

- **RAM:** 8GB minimum (16GB recommended for AI model loading)
- **Storage:** 10GB free space
- **GPU:** Optional (CUDA-compatible for faster AI inference)

---

## Quick Start

For experienced developers, here's the TL;DR:

```bash
# Clone and navigate
git clone https://github.com/your-org/traceiq.git
cd traceiq

# Backend
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
createdb traceiq_db
alembic upgrade head
uvicorn src.main:app --host 0.0.0.0 --port 8001

# Frontend (new terminal)
cd frontend
npm install
npm run dev

# Access at http://localhost:3001
# Login: admin / admin123
```

---

## Detailed Installation

### 1. Clone the Repository

```bash
# Clone the repository
git clone https://github.com/your-org/traceiq.git

# Navigate to project directory
cd traceiq

# Check current branch
git branch
```

**Note:** If cloning from a private repository, ensure you have the necessary access credentials.

---

### 2. Backend Setup

#### 2.1 Create Python Virtual Environment

```bash
cd backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# macOS/Linux:
source venv/bin/activate

# Windows:
venv\Scripts\activate

# Verify activation (should show venv path)
which python
```

#### 2.2 Install Python Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install all dependencies
pip install -r requirements.txt

# Verify installation
pip list
```

**Key Dependencies:**
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `sqlmodel` - ORM with Pydantic integration
- `alembic` - Database migrations
- `torch` & `facenet-pytorch` - AI/ML models
- `pgvector` - Vector similarity search

#### 2.3 Configure Environment Variables

Create a `.env` file in the `backend/` directory:

```bash
# backend/.env
PROJECT_NAME=TraceIQ
API_V1_STR=/api/v1

# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/traceiq_db

# Security
SECRET_KEY=your-super-secret-key-change-this-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS (add production domains later)
BACKEND_CORS_ORIGINS=http://localhost:3001

# Optional: AI Model Config
FACE_DETECTION_DEVICE=mps  # cpu, cuda, or mps (Mac M1/M2)
```

**🔒 Security Note:** Generate a secure `SECRET_KEY` using:
```bash
openssl rand -hex 32
```

---

### 3. Database Setup

#### 3.1 Install PostgreSQL

**macOS (Homebrew):**
```bash
brew install postgresql@14
brew services start postgresql@14
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

**Windows:**
Download and install from [postgresql.org](https://www.postgresql.org/download/windows/)

#### 3.2 Create Database

```bash
# Create database
createdb traceiq_db

# Verify creation
psql -d traceiq_db -c "\dt"
```

#### 3.3 Install pgvector Extension (Optional - for Face Embeddings)

**Note:** Face recognition features require pgvector. If not available, the system will run without face embedding capabilities.

```bash
# Install pgvector
# macOS:
brew install pgvector

# Ubuntu:
sudo apt install postgresql-14-pgvector

# Enable in database
psql -d traceiq_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

#### 3.4 Run Database Migrations

```bash
cd backend

# Activate venv if not already active
source venv/bin/activate

# Run migrations
alembic upgrade head

# Verify tables created
psql -d traceiq_db -c "\dt"
```

**Expected Tables:**
- `stations`
- `users`
- `criminals`
- `cases`
- `offenses`
- `face_embeddings` (if pgvector is installed)

#### 3.5 Create Admin User

```bash
# Option 1: Via SQL
psql -d traceiq_db <<EOF
INSERT INTO users (id, username, email, hashed_password, role, badge_number, is_active, created_at) 
VALUES (
    gen_random_uuid(), 
    'admin', 
    'admin@traceiq.local', 
    '\$2b\$12\$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyKqg6tJe1.K', 
    'ADMIN', 
    'ADMIN001', 
    true, 
    NOW()
);
EOF

# Option 2: Create a Python script (backend/create_admin.py)
# Then run: python create_admin.py
```

**Default Credentials:**
- Username: `admin`
- Password: `admin123`

---

### 4. Frontend Setup

#### 4.1 Install Node Dependencies

```bash
cd frontend

# Install dependencies
npm install

# Verify installation
npm list --depth=0
```

**Key Dependencies:**
- `react` & `react-dom` - UI framework
- `vite` - Build tool
- `react-router-dom` - Routing
- `zustand` - State management
- `tailwindcss` - Styling
- `axios` - HTTP client

#### 4.2 Configure Environment (Optional)

Create `frontend/.env`:

```bash
# frontend/.env
VITE_API_URL=http://localhost:8001/api/v1
```

---

## Running the Application

### Development Mode

#### Start Backend Server

```bash
cd backend
source venv/bin/activate  # Activate venv
uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload
```

**Backend will be available at:**
- API: `http://localhost:8001`
- API Docs: `http://localhost:8001/docs`
- Health Check: `http://localhost:8001/health`

#### Start Frontend Server

Open a **new terminal**:

```bash
cd frontend
npm run dev
```

**Frontend will be available at:**
- Application: `http://localhost:3001`

### Access the Application

1. Navigate to `http://localhost:3001`
2. Login with credentials:
   - **Username:** `admin`
   - **Password:** `admin123`
3. You should see the dashboard with navigation sidebar

---

## Docker Deployment

**Note:** Docker configuration is not yet implemented for this project. Below is a recommended structure for future implementation.

### Planned Docker Setup

Create `docker-compose.yml` in the project root:

```yaml
version: '3.8'

services:
  db:
    image: pgvector/pgvector:pg14
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: traceiq_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  backend:
    build: ./backend
    ports:
      - "8001:8001"
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@db:5432/traceiq_db
    depends_on:
      - db
    command: uvicorn src.main:app --host 0.0.0.0 --port 8001

  frontend:
    build: ./frontend
    ports:
      - "3001:3001"
    depends_on:
      - backend

volumes:
  postgres_data:
```

### Docker Commands (When Implemented)

```bash
# Build and start all services
docker-compose up --build

# Start in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Reset everything (including database)
docker-compose down -v
```

---

## Troubleshooting

### Common Issues

#### 1. Database Connection Refused

**Error:** `asyncpg.exceptions.ConnectionRefusedError`

**Solution:**
```bash
# Check if PostgreSQL is running
pg_ctl status
brew services list  # macOS
sudo systemctl status postgresql  # Linux

# Start PostgreSQL if stopped
brew services start postgresql@14  # macOS
sudo systemctl start postgresql  # Linux
```

#### 2. Port Already in Use

**Error:** `Address already in use`

**Solution:**
```bash
# Find process using port 8001 (backend)
lsof -ti:8001 | xargs kill -9

# Find process using port 3001 (frontend)
lsof -ti:3001 | xargs kill -9
```

#### 3. CORS Errors in Browser

**Error:** `Access to XMLHttpRequest blocked by CORS policy`

**Solution:**
Ensure `backend/src/core/config.py` includes:
```python
BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3001"]
```

#### 4. Python Module Not Found

**Error:** `ModuleNotFoundError: No module named 'xxx'`

**Solution:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

#### 5. Face Embeddings Table Error

**Error:** `type "vector" does not exist`

**Solution:**
This means pgvector is not installed. The app will work without face recognition features. To enable:
```bash
brew install pgvector  # macOS
psql -d traceiq_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

Then uncomment face model imports in:
- `backend/migrations/env.py`
- `backend/migrations/versions/*_initial_migration.py`

---

## Testing

### Backend Tests

```bash
cd backend
source venv/bin/activate

# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_auth.py
```

### Frontend Tests

```bash
cd frontend

# Run tests (if configured)
npm test

# Build for production
npm run build

# Preview production build
npm run preview
```

### Manual Testing Checklist

- [ ] Backend health endpoint returns `{"status": "ok"}`
- [ ] Frontend loads at `http://localhost:3001`
- [ ] Login works with admin credentials
- [ ] Dashboard displays correctly
- [ ] Navigation between pages works
- [ ] API docs accessible at `http://localhost:8001/docs`

---

## Production Deployment

### Environment Preparation

1. **Set production environment variables:**
   - Change `SECRET_KEY` to a secure random value
    - Update `DATABASE_URL` to production database
   - Add production domain to `BACKEND_CORS_ORIGINS`
   - Set `DEBUG=False`

2. **Database:**
   - Use managed PostgreSQL (AWS RDS, Google Cloud SQL, etc.)
   - Enable SSL connections
   - Regular backups

3. **Backend:**
   - Use production ASGI server (Gunicorn with Uvicorn workers)
   - Set up reverse proxy (Nginx)
   - Enable HTTPS
   - Configure logging

4. **Frontend:**
   - Build production bundle: `npm run build`
   - Serve via CDN or static hosting
   - Configure proper cache headers

---

## Additional Resources

- **Project Documentation:** See `/docs` directory
- **API Documentation:** `http://localhost:8001/docs` (when running)
- **Task Tracking:** See `tasks.md`
- **Architecture:** See `ai_architecture.md` and `project_overview.md`

---

## Support

For issues and questions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review existing GitHub issues
3. Create a new issue with:
   - Error message
   - Steps to reproduce
   - System information (OS, Python version, etc.)

---

## License

[Add your license information here]

---

**Last Updated:** February 2026  
**Project Version:** 1.0.0-beta
