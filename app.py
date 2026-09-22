import os
import tempfile
from flask import Flask, request, send_file, jsonify
import yt_dlp

app = Flask(__name__)

@app.get("/")
def home():
    return jsonify({
        "status": "ok",
        "service": "youtube-mp3-n8n"
    })

@app.post("/audio")
def audio():
    data = request.get_json(silent=True) or {}
    url = data.get("url")

    if not url:
        return jsonify({"error": "Falta el campo url"}), 400

    temp_dir = tempfile.mkdtemp()
    output_template = os.path.join(temp_dir, "%(id)s.%(ext)s")

    options = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "noplaylist": True,
        "cookiefile": "/etc/secrets/cookies.txt",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)

        mp3_path = os.path.join(temp_dir, f"{info['id']}.mp3")

        return send_file(
            mp3_path,
            mimetype="audio/mpeg",
            as_attachment=True,
            download_name=f"{info['id']}.mp3"
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
