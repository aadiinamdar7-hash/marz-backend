from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import hashlib
import hmac
import base64
import json
import time
from pymongo import MongoClient

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, allow_headers="*")

# ENV variables
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
JWT_SECRET = os.getenv("JWT_SECRET", "SUPER_SECRET_JWT_KEY")
MONGO_URI = os.getenv("MONGO_URI")

# MongoDB
client = MongoClient(MONGO_URI)
db = client["marz"]
users_col = db["users"]
history_col = db["history"]
settings_col = db["settings"]

# Password hashing
def hash_pw(password):
    return hashlib.sha256(password.encode()).hexdigest()

# JWT
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
    except:
        return None


@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "MARZ backend running"})


# SIGNUP
@app.route("/api/signup", methods=["POST"])
def signup():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    if users_col.find_one({"email": email}):
        return jsonify({"error": "Email already exists"}), 400

    users_col.insert_one({
        "email": email,
        "password": hash_pw(password),
        "created": int(time.time())
    })

    return jsonify({"success": True})


# LOGIN
@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    user = users_col.find_one({"email": email})
    if not user:
        return jsonify({"error": "User not found"}), 404

    if user["password"] != hash_pw(password):
        return jsonify({"error": "Incorrect password"}), 401

    token = create_jwt({
        "email": email,
        "exp": int(time.time()) + 7 * 24 * 3600
    })

    return jsonify({"token": token})


# CHAT
@app.route("/api", methods=["POST"])
def api():
    if request.headers.get("x-api-key") != SECRET_KEY:
        return jsonify({"reply": "Forbidden"}), 403

    token = request.headers.get("Authorization")
    payload = verify_jwt(token)
    if not payload:
        return jsonify({"reply": "Invalid token"}), 401

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

        history_col.insert_one({
            "email": payload["email"],
            "user": user_message,
            "assistant": reply,
            "time": int(time.time())
        })

        return jsonify({"reply": reply})

    except Exception as e:
        print("Error:", e)
        return jsonify({"reply": "Backend error"})


# GET HISTORY
@app.route("/api/history", methods=["GET"])
def history():
    token = request.headers.get("Authorization")
    payload = verify_jwt(token)
    if not payload:
        return jsonify({"error": "Invalid token"}), 401

    chats = list(history_col.find({"email": payload["email"]}).sort("time", 1))
    for c in chats:
        c["_id"] = str(c["_id"])

    return jsonify({"history": chats})


# SAVE SETTINGS
@app.route("/api/settings", methods=["POST"])
def save_settings():
    token = request.headers.get("Authorization")
    payload = verify_jwt(token)
    if not payload:
        return jsonify({"error": "Invalid token"}), 401

    settings = request.json or {}

    settings_col.update_one(
        {"email": payload["email"]},
        {"$set": settings},
        upsert=True
    )

    return jsonify({"success": True})


# GET SETTINGS
@app.route("/api/settings", methods=["GET"])
def get_settings():
    token = request.headers.get("Authorization")
    payload = verify_jwt(token)
    if not payload:
        return jsonify({"error": "Invalid token"}), 401

    s = settings_col.find_one({"email": payload["email"]})
    if not s:
        return jsonify({"settings": {}})

    s["_id"] = str(s["_id"])
    return jsonify({"settings": s})


if __name__ == "__main__":
    app.run(port=3000)
