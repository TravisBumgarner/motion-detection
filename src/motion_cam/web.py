from __future__ import annotations

import re
from dataclasses import asdict

from flask import Flask, abort, jsonify, render_template_string, request, send_from_directory

from motion_cam.config import WebConfig
from motion_cam.storage import StorageManager

CLIPS_PER_PAGE = 20

GALLERY_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Motion Cam</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; background: #111; color: #eee; padding: 1rem; }
  h1 { margin-bottom: 1rem; }
  nav { margin-bottom: 1rem; }
  nav a { color: #6cf; margin-right: 1rem; text-decoration: none; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 1rem; }
  .card { background: #222; border-radius: 8px; overflow: hidden; }
  .card img { width: 100%; aspect-ratio: 16/9; object-fit: cover; }
  .card .info { padding: 0.5rem; font-size: 0.85rem; }
  .card a { color: inherit; text-decoration: none; }
  .pagination { margin-top: 1rem; text-align: center; }
  .pagination a { color: #6cf; margin: 0 0.5rem; }
</style>
</head>
<body>
<h1>Motion Cam</h1>
<nav><a href="/">Gallery</a> <a href="/status">Status</a></nav>
<div class="grid">
{% for clip in clips %}
  <div class="card">
    <a href="/clip/{{ clip.timestamp }}">
      <img src="/media/{{ clip.thumbnail_path }}" alt="Clip {{ clip.timestamp }}">
      <div class="info">{{ clip.display_time }} &mdash; {{ clip.size_kb }} KB</div>
    </a>
  </div>
{% endfor %}
</div>
{% if total_pages > 1 %}
<div class="pagination">
  {% if page > 1 %}<a href="/?page={{ page - 1 }}">&laquo; Prev</a>{% endif %}
  Page {{ page }} / {{ total_pages }}
  {% if page < total_pages %}<a href="/?page={{ page + 1 }}">Next &raquo;</a>{% endif %}
</div>
{% endif %}
</body>
</html>
"""

DETAIL_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Clip {{ clip.timestamp }}</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; background: #111; color: #eee; padding: 1rem; }
  h1 { margin-bottom: 1rem; font-size: 1.2rem; }
  nav { margin-bottom: 1rem; }
  nav a { color: #6cf; margin-right: 1rem; text-decoration: none; }
  video { width: 100%; max-width: 800px; border-radius: 8px; }
  .meta { margin-top: 1rem; }
  .meta dt { font-weight: bold; display: inline; }
  .meta dd { display: inline; margin-right: 1rem; }
  .snapshot { margin-top: 1rem; }
  .snapshot img { width: 100%; max-width: 800px; border-radius: 8px; }
</style>
</head>
<body>
<nav><a href="/">&laquo; Gallery</a> <a href="/status">Status</a></nav>
<h1>Clip {{ clip.display_time }}</h1>
<video controls autoplay>
  <source src="/media/{{ clip.video_path }}" type="video/mp4">
</video>
<dl class="meta">
  <dt>Timestamp:</dt><dd>{{ clip.timestamp }}</dd>
  <dt>Size:</dt><dd>{{ clip.size_kb }} KB</dd>
</dl>
<div class="snapshot">
  <h2>Snapshot</h2>
  <img src="/media/{{ clip.snapshot_path }}" alt="Snapshot">
</div>
</body>
</html>
"""

STATUS_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Status - Motion Cam</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; background: #111; color: #eee; padding: 1rem; }
  h1 { margin-bottom: 1rem; }
  nav { margin-bottom: 1rem; }
  nav a { color: #6cf; margin-right: 1rem; text-decoration: none; }
  dl dt { font-weight: bold; margin-top: 0.5rem; }
  dl dd { margin-left: 1rem; }
</style>
</head>
<body>
<nav><a href="/">&laquo; Gallery</a></nav>
<h1>System Status</h1>
<dl>
  <dt>Total Clips</dt><dd>{{ clip_count }}</dd>
  <dt>Disk Usage</dt><dd>{{ disk_usage_mb }} MB</dd>
</dl>
</body>
</html>
"""


def _format_timestamp(ts: str) -> str:
    """Format YYYYMMDD_HHMMSS into a readable string."""
    return f"{ts[:4]}-{ts[4:6]}-{ts[6:8]} {ts[9:11]}:{ts[11:13]}:{ts[13:15]}"


def _relative_path(absolute_path: str, data_dir: str) -> str:
    """Convert an absolute path to a path relative to the data directory."""
    if absolute_path.startswith(data_dir):
        rel = absolute_path[len(data_dir):]
        return rel.lstrip("/")
    return absolute_path


_TIMESTAMP_RE = re.compile(r"^\d{8}_\d{6}$")


def _validate_timestamp(timestamp: str) -> None:
    """Abort 404 if timestamp doesn't match expected YYYYMMDD_HHMMSS format."""
    if not _TIMESTAMP_RE.match(timestamp):
        abort(404)


def create_app(
    storage_manager: StorageManager,
    web_config: WebConfig,
    data_dir: str,
) -> Flask:
    app = Flask(__name__)
    app.config["DATA_DIR"] = data_dir

    @app.route("/")
    def gallery():
        page = request.args.get("page", 1, type=int)
        all_clips = storage_manager.get_clips()
        total_pages = max(1, -(-len(all_clips) // CLIPS_PER_PAGE))  # ceil division
        start = (page - 1) * CLIPS_PER_PAGE
        end = start + CLIPS_PER_PAGE
        clips = [
            {
                "timestamp": c.timestamp,
                "thumbnail_path": _relative_path(c.thumbnail_path, data_dir),
                "display_time": _format_timestamp(c.timestamp),
                "size_kb": c.file_size // 1024,
            }
            for c in all_clips[start:end]
        ]
        return render_template_string(
            GALLERY_TEMPLATE, clips=clips, page=page, total_pages=total_pages
        )

    @app.route("/clip/<timestamp>")
    def clip_detail(timestamp: str):
        _validate_timestamp(timestamp)
        clip = storage_manager.get_clip(timestamp)
        if clip is None:
            abort(404)
        clip_data = {
            "timestamp": clip.timestamp,
            "display_time": _format_timestamp(clip.timestamp),
            "video_path": _relative_path(clip.path, data_dir),
            "snapshot_path": _relative_path(clip.snapshot_path, data_dir),
            "size_kb": clip.file_size // 1024,
        }
        return render_template_string(DETAIL_TEMPLATE, clip=clip_data)

    @app.route("/status")
    def status_page():
        clips = storage_manager.get_clips()
        disk_usage = storage_manager.get_disk_usage()
        return render_template_string(
            STATUS_TEMPLATE,
            clip_count=len(clips),
            disk_usage_mb=round(disk_usage / (1024 * 1024), 1),
        )

    @app.route("/api/clips")
    def api_clips():
        page = request.args.get("page", 1, type=int)
        all_clips = storage_manager.get_clips()
        start = (page - 1) * CLIPS_PER_PAGE
        end = start + CLIPS_PER_PAGE
        return jsonify([asdict(c) for c in all_clips[start:end]])

    @app.route("/api/clips/<timestamp>", methods=["DELETE"])
    def api_delete_clip(timestamp: str):
        _validate_timestamp(timestamp)
        deleted = storage_manager.delete_clip(timestamp)
        if not deleted:
            abort(404)
        return jsonify({"status": "deleted", "timestamp": timestamp})

    @app.route("/api/status")
    def api_status():
        clips = storage_manager.get_clips()
        disk_usage = storage_manager.get_disk_usage()
        return jsonify({
            "clip_count": len(clips),
            "disk_usage": disk_usage,
        })

    @app.route("/media/<path:filename>")
    def serve_media(filename: str):
        return send_from_directory(data_dir, filename)

    return app
