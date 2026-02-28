# 🐳 Quick Docker Start

## Fast Setup (3 Steps)

1. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env and set secure passwords
   ```

2. **Start all services:**
   ```bash
   docker-compose up --build
   ```

3. **Access:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000/docs
   - Database: localhost:5432

## Useful Commands

```bash
# Stop services
docker-compose down

# View logs
docker-compose logs -f

# Run migrations
docker-compose exec backend alembic upgrade head

# Create admin user
docker-compose exec backend python reset_admin.py
```

**Full guide:** See docker_setup_guide.md in artifacts
