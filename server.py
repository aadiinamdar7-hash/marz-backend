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
    message = data.get("message")

    # Call OpenRouter
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openai/gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are MARZ, a futuristic AI assistant."},
                    {"role": "user", "content": message}
                ]
            }
        )

        ai_reply = response.json()["choices"][0]["message"]["content"]

    except Exception as e:
        ai_reply = "MARZ systems error: unable to reach AI model."

    chat_history.append({
        "user": message,
        "assistant": ai_reply
    })

    return jsonify({"reply": ai_reply})

@app.route("/api/history", methods=["GET"])
def history():
    return jsonify({"history": chat_history})

@app.route("/api/ping")
def ping():
    return "pong"

if __name__ == "__main__":
    app.run(debug=True)
