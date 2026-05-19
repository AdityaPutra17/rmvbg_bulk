import os
import zipfile

from flask import (
    Flask,
    render_template,
    request,
    send_file,
    after_this_request,
    redirect,
    url_for
)

from rembg import remove
from PIL import Image
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "static/output"
ZIP_FOLDER = "static/zips"

TARGET_WIDTH = 343
TARGET_HEIGHT = 447

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(ZIP_FOLDER, exist_ok=True)

def resize_fit_shoulders(image, target_w, target_h):

    alpha = image.split()[-1]
    bbox = alpha.getbbox()

    if bbox:
        image = image.crop(bbox)

    scale = target_h / image.height

    new_w = int(image.width * scale)
    new_h = target_h

    image = image.resize((new_w, new_h), Image.LANCZOS)

    canvas = Image.new(
        "RGBA",
        (target_w, target_h),
        (0, 0, 0, 0)
    )

    x = (target_w - new_w) // 2

    canvas.paste(image, (x, 0), image)

    return canvas
@app.route("/", methods=["GET", "POST"])
def index():

    if request.method == "POST":

        results = []

        files = request.files.getlist("images")

        processed_files = []

        for file in files:

            if file.filename == "":
                continue

            filename = secure_filename(file.filename)

            input_path = os.path.join(
                UPLOAD_FOLDER,
                filename
            )

            base_name = os.path.splitext(filename)[0]

            output_filename = base_name + ".png"

            output_path = os.path.join(
                OUTPUT_FOLDER,
                output_filename
            )

            file.save(input_path)

            with Image.open(input_path).convert("RGBA") as img:

                img_no_bg = remove(img)

                final_img = resize_fit_shoulders(
                    img_no_bg,
                    TARGET_WIDTH,
                    TARGET_HEIGHT
                )

                final_img.save(output_path, "PNG")

            processed_files.append(output_path)

            results.append(
                "output/" + output_filename
            )

        # =========================
        # CREATE ZIP
        # =========================

        date = datetime.now().strftime("%Y%m%d")

        zip_filename = f"foto_{date}.zip"

        zip_path = os.path.join(
            ZIP_FOLDER,
            zip_filename
        )

        with zipfile.ZipFile(
            zip_path,
            "w",
            zipfile.ZIP_DEFLATED
        ) as zipf:

            for file_path in processed_files:

                zipf.write(
                    file_path,
                    arcname=os.path.basename(file_path)
                )

        # =========================
        # SAVE SESSION DATA
        # =========================

        app.config["LAST_RESULTS"] = results
        app.config["LAST_ZIP"] = zip_filename

        # REDIRECT
        return redirect(url_for("index"))

    # GET REQUEST
    results = app.config.get("LAST_RESULTS", [])
    zip_filename = app.config.get("LAST_ZIP", None)

    return render_template(
        "index.html",
        results=results,
        zip_filename=zip_filename
    )

@app.route("/download-zip/<filename>")
def download_zip(filename):

    zip_path = os.path.join(
        ZIP_FOLDER,
        filename
    )

    @after_this_request
    def cleanup(response):

        # =========================
        # DELETE UPLOAD FILES
        # =========================

        for file_name in os.listdir(UPLOAD_FOLDER):

            file_path = os.path.join(
                UPLOAD_FOLDER,
                file_name
            )

            if os.path.isfile(file_path):
                os.remove(file_path)

        # =========================
        # DELETE OUTPUT FILES
        # =========================

        for file_name in os.listdir(OUTPUT_FOLDER):

            file_path = os.path.join(
                OUTPUT_FOLDER,
                file_name
            )

            if os.path.isfile(file_path):
                os.remove(file_path)

        return response

    return send_file(
        zip_path,
        as_attachment=True
    )

if __name__ == "__main__":
    app.run(debug=True)