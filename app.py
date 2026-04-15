"""
Collusion PDF Service — Flask API wrapper around generate-pdf.py
Deploy this to Railway. Exposes:
  POST /generate/invoice   — returns PDF bytes
  POST /generate/manifest  — returns PDF bytes
  POST /generate/both      — returns JSON { invoice: base64, manifest: base64 }
  GET  /health             — health check
"""

import os
import sys
import json
import base64
import tempfile
from pathlib import Path
from flask import Flask, request, Response, jsonify

# generate-pdf.py must be in the same directory as this file
sys.path.insert(0, str(Path(__file__).parent))
from generate_pdf import build_invoice, build_manifest, calc_lines

app = Flask(__name__)

SECRET = os.environ.get("PDF_SERVICE_SECRET", "")


def check_auth():
    """Optional bearer token auth — set PDF_SERVICE_SECRET env var on Railway."""
    if not SECRET:
        return True
    auth = request.headers.get("Authorization", "")
    return auth == f"Bearer {SECRET}"


def generate(order_data: dict, doc_type: str) -> dict:
    """Generate PDF(s) and return as base64 strings."""
    result = {}
    with tempfile.TemporaryDirectory() as tmp:
        oid = order_data["id"].replace("/", "-")

        if doc_type in ("invoice", "both"):
            out_path = os.path.join(tmp, f"{oid}-invoice.pdf")
            build_invoice(order_data, out_path)
            with open(out_path, "rb") as f:
                result["invoice"] = base64.b64encode(f.read()).decode()

        if doc_type in ("manifest", "both"):
            out_path = os.path.join(tmp, f"{oid}-manifest.pdf")
            build_manifest(order_data, out_path)
            with open(out_path, "rb") as f:
                result["manifest"] = base64.b64encode(f.read()).decode()

    return result


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/generate/invoice", methods=["POST"])
def gen_invoice():
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401
    order = request.get_json()
    if not order:
        return jsonify({"error": "No order data"}), 400
    result = generate(order, "invoice")
    pdf_bytes = base64.b64decode(result["invoice"])
    return Response(pdf_bytes, mimetype="application/pdf")


@app.route("/generate/manifest", methods=["POST"])
def gen_manifest():
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401
    order = request.get_json()
    if not order:
        return jsonify({"error": "No order data"}), 400
    result = generate(order, "manifest")
    pdf_bytes = base64.b64decode(result["manifest"])
    return Response(pdf_bytes, mimetype="application/pdf")


@app.route("/generate/both", methods=["POST"])
def gen_both():
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401
    order = request.get_json()
    if not order:
        return jsonify({"error": "No order data"}), 400
    result = generate(order, "both")
    return jsonify(result)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
