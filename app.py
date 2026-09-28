import os
import shutil
import subprocess
import tempfile
from flask import Flask, request, send_file, jsonify

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MUSICA = os.path.join(BASE_DIR, "A_Map_for_the_Quiet (1).mp3")
JOBS_DIR = os.path.join(tempfile.gettempdir(), "spreaker_jobs")
os.makedirs(JOBS_DIR, exist_ok=True)


def safe_job_id(value):
    value = str(value or "")
    limpio = "".join(c for c in value if c.isalnum() or c in ("-", "_"))
    if not limpio:
        raise ValueError("job_id inválido")
    return limpio


@app.get("/")
def home():
    return jsonify({
        "status": "ok",
        "service": "spreaker-audio-mixer-v2"
    })


@app.post("/parte")
def recibir_parte():
    try:
        job_id = safe_job_id(request.form.get("job_id"))
        parte = int(request.form.get("parte", "0"))
        total = int(request.form.get("total", "0"))
        audio = request.files.get("audio")

        if not audio:
            return jsonify({"error": "Falta el archivo audio"}), 400

        if parte < 1 or total < 1 or parte > total:
            return jsonify({"error": "parte/total inválidos"}), 400

        job_dir = os.path.join(JOBS_DIR, job_id)
        os.makedirs(job_dir, exist_ok=True)

        ruta = os.path.join(job_dir, f"parte_{parte:04d}.mp3")
        audio.save(ruta)

        recibidas = len([
            n for n in os.listdir(job_dir)
            if n.startswith("parte_") and n.endswith(".mp3")
        ])

        return jsonify({
            "status": "ok",
            "job_id": job_id,
            "parte": parte,
            "total": total,
            "recibidas": recibidas
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.post("/finalizar")
def finalizar():
    try:
        data = request.get_json(silent=True) or {}
        job_id = safe_job_id(data.get("job_id"))
        total = int(data.get("total", 0))

        if total < 1:
            return jsonify({"error": "total inválido"}), 400

        if not os.path.exists(MUSICA):
            return jsonify({"error": "No se encontró la música de fondo"}), 500

        job_dir = os.path.join(JOBS_DIR, job_id)

        if not os.path.isdir(job_dir):
            return jsonify({"error": "No existe el trabajo solicitado"}), 404

        rutas = [
            os.path.join(job_dir, f"parte_{i:04d}.mp3")
            for i in range(1, total + 1)
        ]

        faltantes = [
            i for i, ruta in enumerate(rutas, start=1)
            if not os.path.exists(ruta)
        ]

        if faltantes:
