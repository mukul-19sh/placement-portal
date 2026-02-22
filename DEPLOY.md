# Phase 5: Deploy to Render + GitHub

## What’s Done

- **PostgreSQL** – `DATABASE_URL` from env (fallback to SQLite locally)
- **Secrets** – `SECRET_KEY` from env
- **Render** – Procfile + gunicorn for production
- **Git** – `.gitignore` for Python/venv/.env

---

## 0. Install Git (if needed)

Download: https://git-scm.com/download/win  
Restart terminal after install.

---

## 1. Push to GitHub

```powershell
cd c:\Users\sharm\OneDrive\Desktop\placement-portal
git init
git add .
git commit -m "Phase 5: PostgreSQL + Render deployment"
```

Create a new repo on GitHub:

1. Go to https://github.com/new
2. **Repository name:** `placement-portal` (or any name)
3. **Public**
4. Do **not** add README, .gitignore, or license
5. Click **Create repository**

Then run (replace `YOUR_REPO_NAME` if different):

```powershell
git remote add origin https://github.com/mukul-19sh/placement-portal.git
git branch -M main
git push -u origin main
```

---

## 2. Deploy on Render

### Option A: Blueprint (PostgreSQL + Web Service)

1. Go to https://dashboard.render.com
2. **New** → **Blueprint**
3. Connect your GitHub account and choose `placement-portal`
4. Render will read `render.yaml` and create:
   - PostgreSQL database (`placement-db`)
   - Web service (`placement-portal-api`)
5. Click **Apply**

### Option B: Manual Setup

**PostgreSQL:**

1. **New** → **PostgreSQL**
2. Name: `placement-db`, Region: Singapore (or closest)
3. **Create Database**
4. Copy **Internal Database URL** (e.g. `postgres://...`)

**Web Service:**

1. **New** → **Web Service**
2. Connect GitHub → select `placement-portal`
3. **Root Directory:** `backend`
4. **Build Command:** `pip install -r requirements.txt`
5. **Start Command:**  
   `gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`
6. **Environment Variables:**
   - `DATABASE_URL` – paste the Internal Database URL
   - `SECRET_KEY` – generate: https://generate-secret.vercel.app/32
7. **Create Web Service**

---

## 3. Update Frontend API URL

After deploy, your API URL will be like:

`https://placement-portal-api.onrender.com`

Update `frontend/js/api.js`:

```javascript
const API_BASE = "https://placement-portal-api.onrender.com";
```

---

## 4. Test & Seed Data

1. Visit `https://placement-portal-api.onrender.com`
   - Should return: `{"message":"Placement Portal API is running"}`
2. Register users via `/auth/register`
3. Add students, jobs, etc. from your frontend or API
