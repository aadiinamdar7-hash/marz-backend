from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import hashlib
import hmac
import base64
import json
import time

app = Flask(__name__)

# Allow all origins
CORS(app, resources={r"/*": {"origins": "*"}}, allow_headers="*")

# ENV variables
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")  # frontend API key
JWT_SECRET = os.getenv("JWT_SECRET", "SUPER_SECRET_JWT_KEY")  # token secret


# -----------------------------
# SIMPLE USER STORAGE (replace with DB later)
# -----------------------------
users = {}  # { "email": "hashed_password" }


def hash_pw(password):
    return hashlib.sha256(password.encode()).hexdigest()


# -----------------------------
# JWT (manual implementation)
# -----------------------------
def create_jwt(payload):
    header = {"alg": "HS256", "typ": "JWT"}

    def b64(data):
        return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=")

    header_b64 = b64(header)
    payload_b64 = b64(payload)

    signature = hmac.new(
        JWT_SECRET.encode(),
        header_b64 + b"." + payload_b64,
        hashlib.sha256
    ).digest()

    signature_b64 = base64.urlsafe_b64encode(signature).rstrip(b"=")

    return f"{header_b64.decode()}.{payload_b64.decode()}.{signature_b64.decode()}"


def verify_jwt(token):
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")

        signature_check = hmac.new(
            JWT_SECRET.encode(),
            f"{header_b64}.{payload_b64}".encode(),
            hashlib.sha256
        ).digest()

        if base64.urlsafe_b64encode(signature_check).rstrip(b"=") != signature_b64.encode():
            return None

        payload_json = base64.urlsafe_b64decode(payload_b64 + "==")
        payload = json.loads(payload_json)

        if payload.get("exp") < int(time.time()):
            return None

        return payload

    except Exception:
        return None


# -----------------------------
# HOME
# -----------------------------
@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "MARZ backend running"})


# -----------------------------
# SIGNUP
# -----------------------------
@app.route("/api/signup", methods=["POST"])
def signup():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Missing fields"}), 400

    if email in users:
        return jsonify({"error": "Email already exists"}), 400

    users[email] = hash_pw(password)
    return jsonify({"success": True})


# -----------------------------
# LOGIN
# -----------------------------
@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    if email not in users:
        return jsonify({"error": "User not found"}), 404

    if users[email] != hash_pw(password):
        return jsonify({"error": "Incorrect password"}), 401

    token = create_jwt({
        "email": email,
        "exp": int(time.time()) + 7 * 24 * 3600  # 7 days
    })

    return jsonify({"token": token})


# -----------------------------
# PROTECTED MARZ AI ENDPOINT
# -----------------------------
@app.route("/api", methods=["POST"])
def api():
    # 1. Check frontend API key
    client_key = request.headers.get("x-api-key")
    if client_key != SECRET_KEY:
        return jsonify({"reply": "Forbidden"}), 403

    # 2. Check JWT token
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"reply": "Unauthorized"}), 401

    payload = verify_jwt(token)
    if not payload:
        return jsonify({"reply": "Invalid token"}), 401

    # 3. Process user message
    user_message = request.json.get("message", "")

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openai/gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "You are MARZ, a helpful AI assistant."},
                    {"role": "user", "content": user_message}
                ]
            }
        )

        data = response.json()
        reply = data["choices"][0]["message"]["content"]
        return jsonify({"reply": reply})

    except Exception as e:
        print("Error:", e)
        return jsonify({"reply": "Backend error"})


if __name__ == "__main__":
    app.run(port=3000)
