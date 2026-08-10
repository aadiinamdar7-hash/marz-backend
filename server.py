from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Set your OpenRouter API key as an environment variable
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

@app.route("/api", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "")

    # Build messages for OpenRouter
    if user_message.startswith("http://") or user_message.startswith("https://"):
        # Treat as image URL
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Please analyze this image."},
                    {"type": "image_url", "image_url": user_message}
                ]
            }
        ]
    elif user_message.startswith("data:image"):
        # Treat as pasted screenshot (base64)
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Please analyze this screenshot."},
                    {"type": "image_url", "image_url": user_message}
                ]
            }
        ]
    else:
        # Treat as plain text
        messages = [{"role": "user", "content": user_message}]

    # Send request to OpenRouter
    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "openrouter/free",  # router picks vision model if needed
            "messages": messages
        }
    )

    if resp.status_code == 200:
        reply = resp.json()["choices"][0]["message"]["content"]
        return jsonify({"reply": reply})
    else:
        return jsonify({"reply": "Error from OpenRouter."}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
