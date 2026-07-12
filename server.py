from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)

# FIX: Allow all CORS + headers
CORS(app, resources={r"/*": {"origins": "*"}}, allow_headers="*")

# ENV VARS
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")  # MUST MATCH FRONTEND EXACTLY


@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "MARZ backend running"})


# FIX: POST ONLY — prevents 405
@app.route("/api", methods=["POST"])
def api():
    client_key = request.headers.get("x-api-key")

    # FIX: Key check
    if client_key != SECRET_KEY:
        return jsonify({"reply": "Forbidden"}), 403

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
