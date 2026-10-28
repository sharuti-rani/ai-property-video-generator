"""
AI Property Video Generator — Flask Web Application
"""
import os
import uuid
import json
import logging
import traceback
from datetime import datetime

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    send_from_directory,
    url_for,
)
from werkzeug.utils import secure_filename

from config import (
    UPLOAD_DIR,
    OUTPUT_DIR,
    STATIC_DIR,
    TEMPLATE_DIR,
    SECRET_KEY,
    MAX_CONTENT_LENGTH,
    ALLOWED_EXTENSIONS,
    MAX_IMAGES,
)
from script_generator import generate_script
from video_generator import generate_video

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(
    __name__,
    static_folder=STATIC_DIR,
    template_folder=TEMPLATE_DIR,
)
app.secret_key = SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/generate", methods=["POST"])
def api_generate():
    """
    Main endpoint — accepts property details + images, returns video.
    Expects multipart/form-data with:
      - property_data: JSON string with property details
      - images: multiple file uploads
    """
    try:
        # --- Parse property data ---
        raw = request.form.get("property_data", "{}")
        try:
            property_data = json.loads(raw)
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid JSON in property_data field"}), 400

        # Parse key_features from comma-separated string if needed
        if isinstance(property_data.get("key_features"), str):
            property_data["key_features"] = [
                f.strip()
                for f in property_data["key_features"].split(",")
                if f.strip()
            ]

        # Validate required fields
        if not property_data.get("property_name"):
            return jsonify({"error": "Property name is required"}), 400

        # --- Handle images ---
        images = request.files.getlist("images")
        if not images or all(f.filename == "" for f in images):
            return jsonify({"error": "At least one property image is required"}), 400

        if len(images) > MAX_IMAGES:
            return jsonify({
                "error": f"Maximum {MAX_IMAGES} images allowed, got {len(images)}"
            }), 400

        # Create a unique job directory
        job_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
        job_upload_dir = os.path.join(UPLOAD_DIR, job_id)
        os.makedirs(job_upload_dir, exist_ok=True)

        saved_images = []
        for img_file in images:
            if img_file and img_file.filename and allowed_file(img_file.filename):
                filename = secure_filename(img_file.filename)
                # Prefix with index to preserve order
                idx = len(saved_images)
                save_name = f"{idx:02d}_{filename}"
                save_path = os.path.join(job_upload_dir, save_name)
                img_file.save(save_path)
                saved_images.append(save_path)
                logger.info(f"Saved image: {save_path}")

        if not saved_images:
            return jsonify({
                "error": "No valid images uploaded. Supported formats: PNG, JPG, JPEG, WEBP"
            }), 400

        # --- Generate script ---
        logger.info(f"Generating script for {len(saved_images)} images...")
        include_narration = property_data.pop("include_narration", True)
        if isinstance(include_narration, str):
            include_narration = include_narration.lower() in ("true", "1", "yes", "on")

        script = generate_script(property_data, len(saved_images))
        logger.info(f"Script generated: {json.dumps(script, indent=2)[:500]}")

        # --- Generate video ---
        output_filename = f"property_video_{job_id}.mp4"
        output_path = os.path.join(OUTPUT_DIR, output_filename)

        generate_video(
            image_paths=saved_images,
            script=script,
            output_path=output_path,
            include_narration=include_narration,
        )

        # --- Return result ---
        return jsonify({
            "success": True,
            "video_url": url_for("serve_video", filename=output_filename),
            "video_filename": output_filename,
            "script": script,
            "job_id": job_id,
            "num_images": len(saved_images),
        })

    except Exception as e:
        logger.error(f"Video generation failed: {traceback.format_exc()}")
        return jsonify({
            "error": f"Video generation failed: {str(e)}",
            "details": traceback.format_exc() if app.debug else None,
        }), 500


@app.route("/output/<filename>")
def serve_video(filename):
    """Serve generated videos."""
    return send_from_directory(OUTPUT_DIR, filename)


@app.route("/api/sample-data")
def sample_data():
    """Return sample property data for the form."""
    sample_path = os.path.join(
        os.path.dirname(__file__), "sample_data", "sample_property.json"
    )
    if os.path.isfile(sample_path):
        with open(sample_path, "r") as f:
            return jsonify(json.load(f))
    return jsonify({
        "property_name": "Sample Property",
        "location": "City Center",
        "price": "$500,000",
        "property_type": "Apartment",
        "key_features": ["Modern Design", "Great Location"],
        "cta_text": "Contact us today!",
    })


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("  AI Property Video Generator")
    logger.info("  Starting on http://localhost:5000")
    logger.info("=" * 60)
    app.run(debug=True, host="0.0.0.0", port=5000)
