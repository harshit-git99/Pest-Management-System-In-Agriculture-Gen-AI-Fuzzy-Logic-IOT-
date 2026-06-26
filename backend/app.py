from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from functools import wraps
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory, session
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from backend.model_adapter import predict_pest
from backend.fuzzy_engine import advisory

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

app = Flask(__name__, static_folder=str(BASE_DIR / "frontend"), static_url_path="")
app.secret_key = os.getenv("APP_SECRET", "dev-secret-change-me")
CORS(app, supports_credentials=True)

DB_PATH = BASE_DIR / "instance" / "agropest.db"
UPLOAD_DIR = BASE_DIR / os.getenv("UPLOAD_FOLDER", "frontend/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row):
    return dict(row) if row else None


def init_db():
    conn = db()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin','farmer')),
            farm_name TEXT,
            location TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            crop_type TEXT NOT NULL,
            field_name TEXT,
            image_path TEXT,
            pest TEXT NOT NULL,
            confidence REAL NOT NULL,
            severity REAL NOT NULL,
            temperature REAL NOT NULL,
            humidity REAL NOT NULL,
            risk TEXT NOT NULL,
            risk_score REAL NOT NULL,
            advice_json TEXT NOT NULL,
            notes TEXT,
            status TEXT DEFAULT 'Open',
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            detection_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            rating INTEGER NOT NULL,
            outcome TEXT NOT NULL,
            comment TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(detection_id) REFERENCES detections(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS sensor_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            field_name TEXT NOT NULL,
            temperature REAL NOT NULL,
            humidity REAL NOT NULL,
            soil_moisture REAL NOT NULL,
            pest_count INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        """
    )
    admin_email = os.getenv("ADMIN_EMAIL", "admin@agropest.local")
    admin_password = os.getenv("ADMIN_PASSWORD", "Admin@123")
    cur.execute("SELECT id FROM users WHERE email=?", (admin_email,))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users(name,email,password_hash,role,farm_name,location,created_at) VALUES (?,?,?,?,?,?,?)",
            ("System Admin", admin_email, generate_password_hash(admin_password), "admin", "AgroPest Control", "HQ", datetime.utcnow().isoformat()),
        )
    conn.commit()
    conn.close()


init_db()


def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    conn = db()
    user = conn.execute("SELECT id,name,email,role,farm_name,location,created_at FROM users WHERE id=?", (uid,)).fetchone()
    conn.close()
    return row_to_dict(user)


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            return jsonify({"error": "Authentication required"}), 401
        return fn(*args, **kwargs)
    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user or user["role"] != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return fn(*args, **kwargs)
    return wrapper


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.get("/")
def root():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/health")
def health():
    return jsonify({"status": "ok", "app": "AgroPest AI"})


@app.post("/api/register")
def register():
    data = request.get_json(force=True)
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    role = data.get("role", "farmer")
    if role not in ("farmer", "admin"):
        role = "farmer"
    if not name or not email or len(password) < 6:
        return jsonify({"error": "Name, valid email and password min 6 characters are required"}), 400
    try:
        conn = db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users(name,email,password_hash,role,farm_name,location,created_at) VALUES (?,?,?,?,?,?,?)",
            (name, email, generate_password_hash(password), role, data.get("farm_name"), data.get("location"), datetime.utcnow().isoformat()),
        )
        conn.commit()
        uid = cur.lastrowid
        conn.close()
        session["user_id"] = uid
        return jsonify({"message": "registered", "user": current_user()})
    except sqlite3.IntegrityError:
        return jsonify({"error": "Email already exists"}), 409


@app.post("/api/login")
def login():
    data = request.get_json(force=True)
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    conn = db()
    user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    conn.close()
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Incorrect email or password"}), 401
    session["user_id"] = user["id"]
    return jsonify({"message": "logged_in", "user": current_user()})


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify({"message": "logged_out"})


@app.get("/api/me")
def me():
    return jsonify({"user": current_user()})


@app.post("/api/detect")
@login_required
def detect():
    user = current_user()
    crop_type = request.form.get("crop_type", "General Crop")
    field_name = request.form.get("field_name", "Field A")
    notes = request.form.get("notes", "")
    temperature = float(request.form.get("temperature", 30))
    humidity = float(request.form.get("humidity", 70))
    image = request.files.get("image")
    if not image or not allowed_file(image.filename):
        return jsonify({"error": "Upload a pest image in PNG/JPG/JPEG/WEBP format"}), 400
    filename = f"{uuid4().hex}_{secure_filename(image.filename)}"
    saved_path = UPLOAD_DIR / filename
    image.save(saved_path)
    pred = predict_pest(str(saved_path), crop_type, notes)
    adv = advisory(pred.pest, pred.severity, temperature, humidity, crop_type)

    import json
    conn = db()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO detections(user_id,crop_type,field_name,image_path,pest,confidence,severity,temperature,humidity,risk,risk_score,advice_json,notes,created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (user["id"], crop_type, field_name, f"/uploads/{filename}", pred.pest, pred.confidence, pred.severity, temperature, humidity, adv["risk"], adv["risk_score"], json.dumps({"prediction": pred.__dict__, "advisory": adv}), notes, datetime.utcnow().isoformat()),
    )
    conn.commit()
    detection_id = cur.lastrowid
    conn.close()
    return jsonify({"id": detection_id, "prediction": pred.__dict__, "advisory": adv, "image_url": f"/uploads/{filename}"})


@app.post("/api/manual-entry")
@login_required
def manual_entry():
    import json
    user = current_user()
    data = request.get_json(force=True)
    pest = data.get("pest", "Aphids")
    severity = float(data.get("severity", 45))
    temperature = float(data.get("temperature", 30))
    humidity = float(data.get("humidity", 70))
    crop_type = data.get("crop_type", "General Crop")
    field_name = data.get("field_name", "Field A")
    adv = advisory(pest, severity, temperature, humidity, crop_type)
    conn = db()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO detections(user_id,crop_type,field_name,image_path,pest,confidence,severity,temperature,humidity,risk,risk_score,advice_json,notes,created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (user["id"], crop_type, field_name, None, pest, 1.0, severity, temperature, humidity, adv["risk"], adv["risk_score"], json.dumps({"manual": True, "advisory": adv}), data.get("notes", ""), datetime.utcnow().isoformat()),
    )
    conn.commit()
    detection_id = cur.lastrowid
    conn.close()
    return jsonify({"id": detection_id, "advisory": adv})


@app.get("/api/detections")
@login_required
def detections():
    user = current_user()
    conn = db()
    if user["role"] == "admin":
        rows = conn.execute("SELECT d.*, u.name farmer_name, u.location FROM detections d JOIN users u ON u.id=d.user_id ORDER BY d.id DESC LIMIT 200").fetchall()
    else:
        rows = conn.execute("SELECT d.*, u.name farmer_name, u.location FROM detections d JOIN users u ON u.id=d.user_id WHERE d.user_id=? ORDER BY d.id DESC LIMIT 100", (user["id"],)).fetchall()
    conn.close()
    return jsonify({"detections": [row_to_dict(r) for r in rows]})


@app.post("/api/feedback")
@login_required
def add_feedback():
    user = current_user()
    data = request.get_json(force=True)
    conn = db()
    conn.execute(
        "INSERT INTO feedback(detection_id,user_id,rating,outcome,comment,created_at) VALUES (?,?,?,?,?,?)",
        (int(data["detection_id"]), user["id"], int(data.get("rating", 5)), data.get("outcome", "pending"), data.get("comment", ""), datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "feedback_saved"})


@app.post("/api/sensor-log")
@login_required
def sensor_log():
    user = current_user()
    data = request.get_json(force=True)
    conn = db()
    conn.execute(
        "INSERT INTO sensor_logs(user_id,field_name,temperature,humidity,soil_moisture,pest_count,created_at) VALUES (?,?,?,?,?,?,?)",
        (user["id"], data.get("field_name", "Field A"), float(data.get("temperature", 30)), float(data.get("humidity", 70)), float(data.get("soil_moisture", 40)), int(data.get("pest_count", 0)), datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "sensor_log_saved"})


@app.get("/api/admin/stats")
@admin_required
def admin_stats():
    conn = db()
    total_farmers = conn.execute("SELECT COUNT(*) c FROM users WHERE role='farmer'").fetchone()["c"]
    total = conn.execute("SELECT COUNT(*) c FROM detections").fetchone()["c"]
    severe = conn.execute("SELECT COUNT(*) c FROM detections WHERE risk='Severe'").fetchone()["c"]
    open_cases = conn.execute("SELECT COUNT(*) c FROM detections WHERE status='Open'").fetchone()["c"]
    top_pests = conn.execute("SELECT pest, COUNT(*) count FROM detections GROUP BY pest ORDER BY count DESC LIMIT 5").fetchall()
    conn.close()
    return jsonify({"total_farmers": total_farmers, "detections": total, "severe": severe, "open_cases": open_cases, "top_pests": [row_to_dict(r) for r in top_pests]})


@app.get("/api/admin/users")
@admin_required
def admin_users():
    conn = db()
    rows = conn.execute("SELECT id,name,email,role,farm_name,location,created_at FROM users ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify({"users": [row_to_dict(r) for r in rows]})


@app.post("/api/admin/detection/<int:detection_id>/status")
@admin_required
def update_status(detection_id):
    data = request.get_json(force=True)
    status = data.get("status", "Open")
    if status not in ("Open", "Under Review", "Resolved", "Escalated"):
        return jsonify({"error": "Invalid status"}), 400
    conn = db()
    conn.execute("UPDATE detections SET status=? WHERE id=?", (status, detection_id))
    conn.commit()
    conn.close()
    return jsonify({"message": "status_updated"})


@app.get("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
