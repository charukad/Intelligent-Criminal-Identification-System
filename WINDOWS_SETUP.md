# 🪟 Running TraceIQ on Windows

This guide shows how to run the dockerized TraceIQ application on Windows.

## 📋 Prerequisites

### 1. Install Docker Desktop for Windows

**Download**: https://www.docker.com/products/docker-desktop/

**System Requirements**:
- Windows 10/11 (64-bit)
- WSL 2 (Windows Subsystem for Linux)
- Virtualization enabled in BIOS

**Installation Steps**:
1. Download Docker Desktop installer
2. Run the installer
3. Enable WSL 2 during installation (recommended)
4. Restart your computer
5. Launch Docker Desktop
6. Wait for Docker to start (whale icon in system tray)

### 2. Install Git (Optional)

If you want to clone the repository:
- Download from: https://git-scm.com/download/win
- Or use GitHub Desktop: https://desktop.github.com/

---

## 📦 Getting the Project

### Option 1: Copy Project Files

1. **Transfer the entire project folder** to your Windows PC
   - Use USB drive, cloud storage, or network transfer
   - Recommended location: `C:\Users\YourName\Documents\face`

### Option 2: Git Clone (if using Git)

```powershell
git clone <repository-url> C:\Users\YourName\Documents\face
cd C:\Users\YourName\Documents\face
```

---

## ⚙️ Configuration

### 1. Create `.env` File

Open PowerShell in the project directory:

```powershell
cd C:\Users\YourName\Documents\face
copy .env.example .env
```

### 2. Edit `.env` File

Open `.env` with Notepad or VS Code and update:

```env
# Database Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_DB=traceiq_db

# Backend Configuration
DATABASE_URL=postgresql://postgres:your_secure_password_here@db:5432/traceiq_db
SECRET_KEY=your_generated_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS (use your frontend URL)
CORS_ORIGINS=http://localhost:3000

# Frontend Configuration
VITE_API_URL=http://localhost:8000
```

**Generate a secure SECRET_KEY**:
```powershell
# In PowerShell
-join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | % {[char]$_})
```

---

## 🚀 Running the Application

### Start All Services

Open **PowerShell** or **Command Prompt** in the project directory:

```powershell
# Navigate to project
cd C:\Users\YourName\Documents\face

# Start all containers (first time - will build images)
docker-compose up --build -d
```

**First-time build takes ~5 minutes** (downloads dependencies)

### Check Container Status

```powershell
docker-compose ps
```

**Expected output**:
```
NAME               STATUS          PORTS
traceiq-backend    Up (healthy)    0.0.0.0:8000->8000/tcp
traceiq-db         Up (healthy)    0.0.0.0:5432->5432/tcp
traceiq-frontend   Up (healthy)    0.0.0.0:3000->80/tcp
```

### View Logs

```powershell
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
```

---

## 🌐 Access the Application

Once containers are running:

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000/docs
- **Database**: localhost:5432

---

## 🔧 Common Commands

### Stop Services

```powershell
docker-compose down
```

### Restart Services

```powershell
docker-compose restart
```

### Rebuild After Code Changes

```powershell
docker-compose up --build
```

### View Container Logs

```powershell
# Real-time logs
docker-compose logs -f backend

# Last 50 lines
docker-compose logs --tail=50 backend
```

### Database Operations

```powershell
# Run migrations
docker-compose exec backend alembic upgrade head

# Create admin user
docker-compose exec backend python reset_admin.py

# Access database shell
docker-compose exec db psql -U postgres -d traceiq_db
```

### Clean Everything (Reset)

```powershell
# Stop and remove containers, networks
docker-compose down

# Remove volumes (WARNING: deletes database data)
docker-compose down -v

# Remove all images
docker-compose down --rmi all
```

---

## 🐛 Troubleshooting

### Port Already in Use

**Error**: `Bind for 0.0.0.0:3000 failed: port is already allocated`

**Solution**:
```powershell
# Find process using port 3000
netstat -ano | findstr :3000

# Kill the process (replace PID with actual process ID)
taskkill /PID <PID> /F
```

### Docker Desktop Not Running

**Error**: `Cannot connect to the Docker daemon`

**Solution**:
1. Open Docker Desktop from Start Menu
2. Wait for Docker to start (whale icon in system tray turns solid)
3. Try the command again

### WSL 2 Issues

**Error**: `WSL 2 installation is incomplete`

**Solution**:
1. Open PowerShell as Administrator:
   ```powershell
   wsl --install
   wsl --update
   ```
2. Restart your computer
3. Launch Docker Desktop

### "Access Denied" Errors

**Solution**: Run PowerShell/Command Prompt as **Administrator**

### Slow Build Times

**Tip**: Docker builds are slower on first run. Subsequent builds use cache and are much faster.

**Optimization**:
- Enable WSL 2 backend in Docker Desktop settings
- Allocate more CPU/Memory to Docker Desktop:
  - Settings → Resources → Adjust sliders

---

## 📂 Project Structure (Windows Paths)

```
C:\Users\YourName\Documents\face\
├── backend\
│   ├── Dockerfile          ✅ Backend container config
│   ├── src\                   Backend code
│   ├── requirements.txt       Python dependencies
│   └── init.sql               Database initialization
├── frontend\
│   ├── Dockerfile          ✅ Frontend container config
│   ├── nginx.conf             Nginx configuration
│   ├── src\                   React code
│   └── package.json           Node dependencies
├── docker-compose.yml      ✅ Main orchestration file
├── .env                    ✅ Your configuration
└── .env.example               Configuration template
```

---

## 🎯 Quick Start Checklist

- [ ] Install Docker Desktop for Windows
- [ ] Enable WSL 2 (if prompted)
- [ ] Copy/clone project to Windows
- [ ] Create `.env` file from `.env.example`
- [ ] Set secure passwords in `.env`
- [ ] Run `docker-compose up --build -d`
- [ ] Wait ~5 minutes for first build
- [ ] Access http://localhost:3000

---

## 💡 Tips for Windows Users

### Use Windows Terminal (Recommended)

Modern, better than Command Prompt:
- Download from Microsoft Store: "Windows Terminal"
- Supports tabs, better copy/paste, nice themes

### File Paths in Docker

Docker automatically converts Windows paths:
- Windows: `C:\Users\YourName\Documents\face`
- Docker sees: `/c/Users/YourName/Documents/face`

### Performance

For **best performance**:
1. Enable WSL 2 backend (Docker Desktop → Settings → General)
2. Store project in WSL 2 filesystem (optional, advanced):
   ```powershell
   wsl
   cd ~
   git clone <repo>
   ```

### Firewall Warnings

Windows Firewall may ask for permission when Docker starts:
- ✅ Allow Docker Desktop
- ✅ Allow Docker Backend

---

## 🆘 Need Help?

1. **Check container logs**: `docker-compose logs -f`
2. **Verify Docker is running**: Check system tray for whale icon
3. **Restart Docker Desktop**: Right-click whale icon → Restart
4. **Check documentation**: Full guide in `docker_setup_guide.md`

---

## 🚀 Next Steps

Once running:
1. Create admin user: `docker-compose exec backend python reset_admin.py`
2. Login at http://localhost:3000
3. Upload images and test facial recognition
4. Add your trained TraceNet model to `backend\models\` folder

**The exact same Docker setup works on Mac, Windows, and Linux!** 🎉
