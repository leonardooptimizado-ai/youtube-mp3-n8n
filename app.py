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
        "extractor_args": {
            "youtube": {
                "player_client": ["mweb"]
            }
        },
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)

        mp3_path = os.path.join(
            temp_dir,
            f"{info['id']}.mp3"
        )

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
        # Recibe todas las partes de voz desde n8n
        archivos = request.files.getlist("audios")

        if not archivos:
            return jsonify({
                "error": "No se recibieron audios"
            }), 400

        # Música permanente incluida en el repositorio
        musica_path = os.path.join(
            os.path.dirname(__file__),
            "A_Map_for_the_Quiet (1).mp3"
        )

        if not os.path.exists(musica_path):
            return jsonify({
                "error": "No se encontró la música de fondo"
            }), 500

        # Guardar las partes de voz respetando su orden
        rutas_audio = []

        for i, archivo in enumerate(archivos):
            ruta = os.path.join(
                temp_dir,
                f"parte_{i:03d}.mp3"
            )
            archivo.save(ruta)
            rutas_audio.append(ruta)

        # Crear lista para FFmpeg
        lista_path = os.path.join(
            temp_dir,
            "lista.txt"
        )

        with open(lista_path, "w", encoding="utf-8") as f:
            for ruta in rutas_audio:
                f.write(f"file '{ruta}'\n")

        # Unir todas las partes de voz
        voz_unida = os.path.join(
            temp_dir,
            "voz_unida.mp3"
        )

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

        # Mezclar narración + música de fondo
        salida = os.path.join(
            temp_dir,
            "episodio_final.mp3"
        )

        subprocess.run([
            "ffmpeg",
            "-i", voz_unida,
            "-stream_loop", "-1",
            "-i", musica_path,
            "-filter_complex",
            "[1:a]volume=0.06[m];"
            "[0:a][m]amix=inputs=2:"
            "duration=first:dropout_transition=2",
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            "-y",
            salida
        ], check=True)

        return send_file(
            salida,
            mimetype="audio/mpeg",
            as_attachment=True,
            download_name="episodio_final.mp3"
        )

    except subprocess.CalledProcessError as e:
        return jsonify({
            "error": "FFmpeg no pudo procesar el audio",
            "details": str(e)
        }), 500

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(
        host="0.0.0.0",
        port=port
    )
