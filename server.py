#!/usr/bin/env python3
"""
VEHIQ — Vehicle lookup proxy server

Local:  python server.py  → http://localhost:5000
Render: auto-detects PORT env variable, no SSL needed (Render handles HTTPS)
"""

from flask import Flask, jsonify, request, send_file  # type: ignore
import requests  # type: ignore
import os, socket, tempfile, subprocess

app = Flask(__name__)

# ── Obfuscated config (XOR encoded) ──────────────────────────────────────────
_K = [110,135,149,142,52,192,80,195,80,96,177,51,172,149,118,200]
_B = [6,243,225,254,71,250,127,236,51,1,195,30,193,252,14,229,8,226,240,163,80,165,61,172,126,22,212,65,207,240,26,230,15,247,229]
_A = [42,194,216,193]
_d = lambda v: ''.join(chr(c ^ _K[i % len(_K)]) for i, c in enumerate(v))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_file(os.path.join(BASE_DIR, "index.html"))

@app.route("/api/vehicle")
def vehicle():
    rc = request.args.get("rc", "").strip().upper()
    if not rc:
        return jsonify({"error": "rc parameter is required"}), 400

    url = f"{_d(_B)}/?rc={rc}&key={_d(_A)}"
    print(f"[VEHIQ] Fetching RC: {rc}")
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return jsonify(resp.json())
    except requests.exceptions.Timeout:
        return jsonify({"error": "Request timed out"}), 504
    except requests.exceptions.HTTPError as e:
        return jsonify({"error": f"API returned HTTP {e.response.status_code}"}), 502
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── SSL cert generator (local only) ──────────────────────────────────────────

def generate_self_signed_cert():
    cert_dir  = tempfile.mkdtemp()
    cert_file = os.path.join(cert_dir, "cert.pem")
    key_file  = os.path.join(cert_dir, "key.pem")
    try:
        subprocess.run([
            "openssl", "req", "-x509", "-newkey", "rsa:2048",
            "-keyout", key_file, "-out", cert_file,
            "-days", "365", "-nodes", "-subj", "/CN=vehiq-local"
        ], check=True, capture_output=True)
        return cert_file, key_file
    except Exception as e:
        print(f"[VEHIQ] openssl not available: {e}")
        return None, None

# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    is_render = os.environ.get("RENDER") == "true"

    # On Render: plain HTTP, Render handles HTTPS termination externally
    if is_render:
        print(f"[VEHIQ] Running on Render — port {port}, HTTP (Render handles HTTPS)")
        app.run(host="0.0.0.0", port=port, debug=False)

    # Local: try HTTPS via self-signed cert for mobile camera support
    else:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except:
            local_ip = "127.0.0.1"

        cert_file, key_file = generate_self_signed_cert()

        if cert_file:
            print(f"""
  ╔══════════════════════════════════════════════════╗
  ║           VEHIQ — VEHICLE INTELLIGENCE           ║
  ╠══════════════════════════════════════════════════╣
  ║  Local :  https://localhost:{port}               ║
  ║  Mobile:  https://{local_ip}:{port}              ║
  ╠══════════════════════════════════════════════════╣
  ║  On mobile: tap Advanced → Proceed (cert warn)   ║
  ║  is normal — camera WILL work!                   ║
  ╚══════════════════════════════════════════════════╝
            """)
            app.run(host="0.0.0.0", port=port, debug=False,
                    ssl_context=(cert_file, key_file))
        else:
            print(f"""
  ╔══════════════════════════════════════════════════╗
  ║           VEHIQ — VEHICLE INTELLIGENCE           ║
  ╠══════════════════════════════════════════════════╣
  ║  Local :  http://localhost:{port}                ║
  ║  Mobile:  http://{local_ip}:{port}               ║
  ╠══════════════════════════════════════════════════╣
  ║  HTTP mode — camera won't work on mobile         ║
  ║  Install openssl to enable HTTPS locally.        ║
  ╚══════════════════════════════════════════════════╝
            """)
            app.run(host="0.0.0.0", port=port, debug=False)