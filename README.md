# AgroPest AI – Precision Pest Management System

A ready-to-deploy working model for an AI + Fuzzy Logic pest management platform. It includes farmer registration/login, AI pest image upload, fuzzy risk advisory, manual pest entry, sensor logs, feedback, detection history, and admin monitoring.

## Built From The Research Scope

The implementation follows the research-paper modules: user module, data acquisition, preprocessing/identification, decision and advisory, and feedback. It also keeps the system extensible for CNN, IoT and remote sensing integration.

## Features

- Farmer and admin authentication
- Crop/pest image upload
- Working AI model adapter with demo heuristic inference
- Fuzzy logic risk score and advisory engine
- Manual pest entry when camera/internet image upload is not available
- Detection history with search
- Feedback capture for continuous improvement
- Sensor log endpoint for IoT-style field readings
- Admin dashboard for users, detections, severe alerts and case status
- SQLite default database for easy deployment
- Docker, Gunicorn and Render-style deployment files included

## Demo Credentials

Admin:

```text
Email: admin@agropest.local
Password: Admin@123
```

Optional seeded farmer after running `python scripts/seed.py`:

```text
Email: farmer@example.com
Password: Farmer@123
```

## Local Setup

```bash
cd agropest_ai
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
python scripts/seed.py
python -m backend.app
```

Open:

```text
http://localhost:8000
```

## Deploy With Docker

```bash
docker build -t agropest-ai .
docker run -p 8000:8000 --env-file .env agropest-ai
```

## Deploy On Render / Railway / VPS

Use:

```bash
gunicorn backend.app:app
```

Required environment variables:

```text
APP_SECRET=your-strong-secret
DATABASE_URL=sqlite:///instance/agropest.db
UPLOAD_FOLDER=frontend/uploads
ADMIN_EMAIL=admin@yourdomain.com
ADMIN_PASSWORD=ChangeThisStrongPassword
```

For real production, replace SQLite with PostgreSQL/MySQL and move uploads to S3/GCS.

