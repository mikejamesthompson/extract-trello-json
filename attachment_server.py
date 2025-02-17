from flask import Flask, send_from_directory, abort
import os
import humanize
app = Flask(__name__)

TOTAL_FILE_SIZE = 0

@app.route("/<path:file_name>")
def serve_attachment(file_name: str):
    """
    Serves the image file from the attachments directory.
    """

    file_path = os.path.join(os.getenv("ATTACHMENT_DIRECTORY"), file_name)

    try:
        file_size = os.path.getsize(file_path)
        global TOTAL_FILE_SIZE
        TOTAL_FILE_SIZE += file_size
        print(f"👇 Following file's size: {humanize.naturalsize(file_size)} --- Total file size sent: {humanize.naturalsize(TOTAL_FILE_SIZE)}")

        # The send_from_directory helper safely serves files.
        return send_from_directory(os.getenv("ATTACHMENT_DIRECTORY"), file_name)
    except FileNotFoundError:
        abort(404)

@app.route("/")
def index():
    return "Hello!"

if __name__ == "__main__":
    # Run the server on all interfaces at port 3000.
    print("Starting image server on http://0.0.0.0:3000")
    app.run(host="0.0.0.0", port=3000)
