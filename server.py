from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import logging

app = Flask(__name__)
CORS(app)

app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
logging.basicConfig(level=logging.INFO)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
chat_history = []

@app.route("/api", methods=["POST"])
def chat():
    data = request.get_json()
    message = data.get("message", "")

    # Save user message into history
    chat_history.append({"role": "user", "content": str(message)})

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openrouter/free",
                "messages": [{"role": "system", "content": "You are MARZ, a futuristic AI assistant."}] + chat_history
            },
            timeout=30
        )
        ai_reply = response.json()["choices"][0]["message"]["content"]
        # Save assistant reply into history
        chat_history.append({"role": "assistant", "content": ai_reply})
    except Exception as e:
        logging.error(f"Error contacting OpenRouter: {e}")
        ai_reply = f"MARZ systems error: {str(e)}"

    return jsonify({"reply": ai_reply})

@app.route("/api/history", methods=["GET"])
def history():
    return jsonify({"history": chat_history})

@app.route("/api/ping")
def ping():
    return "pong"

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"reply": "Image too large. Please paste a smaller screenshot."}), 413

@app.errorhandler(Exception)
def handle_exception(e):
    logging.error(f"Unexpected error: {e}")
    return jsonify({"reply": "MARZ systems error: unexpected backend issue."}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
