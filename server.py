from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

chat_history = []

@app.route("/api", methods=["POST"])
def chat():
    data = request.get_json()
    message = data.get("message")

    reply = "MARZ: I received your message — " + message

    chat_history.append({
        "user": message,
        "assistant": reply
    })

    return jsonify({"reply": reply})

@app.route("/api/history", methods=["GET"])
def history():
    return jsonify({"history": chat_history})

@app.route("/api/ping")
def ping():
    return "pong"

if __name__ == "__main__":
    app.run(debug=True)
