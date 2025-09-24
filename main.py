# main.py
from flask import Flask, send_from_directory
import os

# Flask app banate hain
app = Flask(__name__, static_folder="public")

# Home route
@app.route("/")
def home():
    return "🚀 Server chal raha hai!"

# Serve file.txt
@app.route("/file.txt")
def file_txt():
    return send_from_directory(app.static_folder, "file.txt")

# Server start
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
