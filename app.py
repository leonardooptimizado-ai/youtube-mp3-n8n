import os
import tempfile
import shutil
import subprocess
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
    cookies_path = os.path.join(temp_dir, "cookies.txt")
    shutil.copy("/etc/secrets/cookies.txt", cookies_path)
    output_template = os.path.join(temp_dir, "%(id)s.%(ext)s")

    options = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "noplaylist": True,
        "cookiefile": cookies_path,
        "extractor_args": {"youtube": {"player_client": ["mweb"]}},
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

@app.post("/mezclar")
def mezclar():
    temp_dir = tempfile.mkdtemp()

    try:
        archivos = request.files.getlist("audios")
        musica = request.files.get("musica")

        if not archivos:
            return jsonify({"error": "No se recibieron audios"}), 400

        rutas_audio = []

        for i, archivo in enumerate(archivos):
            ruta = os.path.join(temp_dir, f"parte_{i:03d}.mp3")
            archivo.save(ruta)
            rutas_audio.append(ruta)

        lista_path = os.path.join(temp_dir, "lista.txt")

        with open(lista_path, "w", encoding="utf-8") as f:
            for ruta in rutas_audio:
                f.write(f"file '{ruta}'\n")

        voz_unida = os.path.join(temp_dir, "voz_unida.mp3")

        subprocess.run([
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", lista_path,
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            "-y",
            voz_unida
        ], check=True)

        if musica:
            musica_path = os.path.join(temp_dir, "musica.mp3")
            musica.save(musica_path)

            salida = os.path.join(temp_dir, "episodio_final.mp3")

            subprocess.run([
                "ffmpeg",
                "-i", voz_unida,
                "-stream_loop", "-1",
                "-i", musica_path,
                "-filter_complex",
                "[1:a]volume=0.10[m];[0:a][m]amix=inputs=2:duration=first:dropout_transition=2",
                "-c:a", "libmp3lame",
                "-b:a", "192k",
                "-y",
                salida
            ], check=True)

        else:
            salida = voz_unida

        return send_file(
            salida,
            mimetype="audio/mpeg",
            as_attachment=True,
            download_name="episodio_final.mp3"
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
