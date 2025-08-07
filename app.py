from flask import Flask, jsonify
import threading
import logging
from main import main as run_main_automation

app = Flask(__name__)

if __name__ != "__main__":
    gunicorn_logger = logging.getLogger("gunicorn.error")
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)

@app.route("/", methods=["POST"])
def trigger_automation():
    app.logger.info("Received API request to trigger automation.")
    thread = threading.Thread(target=run_main_automation)
    thread.start()
    return jsonify({"status": "success", "message": "Automation triggered in the background."}), 202

if __name__ == "__main__":
    app.run(debug=True, port=8080)
