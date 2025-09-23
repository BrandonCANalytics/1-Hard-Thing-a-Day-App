# 🎯 1 Hard Thing a Day

> A simple FastAPI web app that helps you pick a daily challenge to build resilience, discipline, and grit.  
> Deployed on [Fly.io](https://fly.io/) with a managed Postgres database on [Neon](https://neon.tech/).

---

## 🚀 Live Demo
👉 [https://one-hard-thing.fly.dev](https://one-hard-thing.fly.dev)

---

## 📖 About

This project started as a personal side experiment:  
- I wanted a **menu of “hard things”** (e.g. cold shower, early wake-up, 24-hr fast).  
- Each day, I “spin” for a challenge — sometimes a single task, sometimes a pair of half-tasks.  
- Anyone can submit new challenge ideas; I can review and approve them in the backend.

It grew into my **first full-stack deployment** project:
- API built with **FastAPI**  
- Database powered by **Postgres (Neon)**  
- Hosted on **Fly.io** with Docker  
- Styled with **Tailwind CSS**  
- CI/CD + version control with **Git + GitHub**

---

## ✨ Features

- 🎲 **Random Challenge Spinner** — get a full challenge or a combo of two half-challenges.  
- 📝 **Submit New Challenges** — users can propose ideas (moderated).  
- ✅ **Admin Approval Flow** — keep the catalog curated.  
- 🌐 **Live Deployment** — real backend + database, not just local.  
- ⚡ **Lightweight UI** — single-page frontend embedded in FastAPI.

---

## 🛠️ Tech Stack

- **Backend**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.11)  
- **Database**: [Neon](https://neon.tech/) Postgres (async with SQLAlchemy + asyncpg)  
- **Frontend**: Inline HTML/JS + TailwindCSS  
- **Deployment**: [Fly.io](https://fly.io/) (Dockerized app, health checks, scaling)  
- **Infra**: GitHub for source control, CI/CD experiments with Fly  
- **Secrets/Config**: `.env` locally, Fly secrets in prod

---

## 🏗️ How It Works

1. **Randomizer logic**  
   - Items are stored with `is_half` flags.  
   - Spinner returns either one full challenge or two half-challenges.  

2. **Submission system**  
   - User suggestions go into a `submissions` table.  
   - Admin (me) can approve them → they move into the live `items` catalog.  

3. **Deployment flow**  
   - Local dev with `uvicorn app:app --reload`.  
   - Dockerfile for consistent build.  
   - Fly.io manages scaling + HTTPS.  
   - Neon handles Postgres hosting with auto-sleep when idle.  

---

## 🔧 Local Development

Clone and run:

```bash
git clone https://github.com/<your-username>/1HTAD.git
cd 1HTAD

# Create venv
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows

# Install deps
pip install -r requirements.txt

# Create .env
echo "DATABASE_URL=postgresql+asyncpg://user:pass@host/db" > .env

# Run app
uvicorn app:app --reload
