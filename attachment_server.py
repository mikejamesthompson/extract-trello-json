from flask import Flask, send_from_directory, abort
import os

app = Flask(__name__)

@app.route("/<path:filename>")
def serve_attachment(filename: str):
    """
    Serves the image file from the attachments directory.
    """
    try:
        # The send_from_directory helper safely serves files.
        return send_from_directory(os.getenv("ATTACHMENT_DIRECTORY"), filename)
    except FileNotFoundError:
        abort(404)

@app.route("/")
def index():
    return "Hello!"

if __name__ == "__main__":
    # Run the server on all interfaces at port 3000.
    print("Starting image server on http://0.0.0.0:3000")
    app.run(host="0.0.0.0", port=3000)
