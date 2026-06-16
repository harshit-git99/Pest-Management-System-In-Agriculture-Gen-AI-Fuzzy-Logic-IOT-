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

