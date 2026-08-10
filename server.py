from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

chat_history = []

@app.route("/api", methods=["POST"])
def chat():
    data = request.get_json()
    message = data.get("message", "")

    system_prompt = {"role": "system", "content": "You are MARZ, a futuristic AI assistant."}

    # If message contains both image and text, split them
    if "data:image" in message or message.startswith("http://") or message.startswith("https://"):
        parts = message.split(" ", 1)  # split into [image, text] if text exists
        image_part = parts[0]
        text_part = parts[1] if len(parts) > 1 else ""

        messages = [
            system_prompt,
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": text_part if text_part else "Please analyze this image."},
                    {"type": "image_url", "image_url": image_part}
                ]
            }
        ]
    else:
        # Plain text only
        messages = [
            system_prompt,
            {"role": "user", "content": message}
        ]

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openrouter/free",
                "messages": messages
            }
        )
        ai_reply = response.json()["choices"][0]["message"]["content"]
    except Exception:
        ai_reply = "MARZ systems error: unable to reach AI model."

    chat_history.append({"user": message, "assistant": ai_reply})
    return jsonify({"reply": ai_reply})

@app.route("/api/history", methods=["GET"])
def history():
    return jsonify({"history": chat_history})

@app.route("/api/ping")
def ping():
    return "pong"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
