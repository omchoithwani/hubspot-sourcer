"""
Flask web app — provides the search UI and job status API.

Routes:
  GET  /              → search page
  POST /run           → start a search job, returns {job_id}
  GET  /status/<id>   → poll job progress + results
"""

import threading
import uuid
import logging

from flask import Flask, jsonify, render_template, request

from runner import run_search

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

app = Flask(__name__)

# In-memory job store — sufficient for single-instance use.
# Keys are job IDs; values are the job dicts mutated by run_search().
_jobs: dict = {}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/run", methods=["POST"])
def run():
    data = request.get_json(silent=True) or {}
    query = (data.get("query") or "").strip()
    if not query:
        return jsonify({"error": "Query is required"}), 400

    job_id = uuid.uuid4().hex[:10]
    job = {
        "id": job_id,
        "query": query,
        "status": "running",
        "progress": "Starting…",
        "stats": {"found": 0, "live": 0, "new": 0, "confirmed": 0, "pushed": 0},
        "results": [],
        "error": None,
    }
    _jobs[job_id] = job

    def _worker():
        try:
            run_search(query, job)
        except Exception as exc:
            job["status"] = "error"
            job["error"] = str(exc)
            job["progress"] = f"Error: {exc}"

    threading.Thread(target=_worker, daemon=True).start()
    return jsonify({"job_id": job_id})


@app.route("/status/<job_id>")
def status(job_id: str):
    job = _jobs.get(job_id)
    if job is None:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
