#!/usr/bin/env python3
"""
VEHIQ — Vehicle lookup proxy server
Run: python server.py
Then open: https://YOUR_PC_IP:5000  (note: https not http)

On mobile, your browser will warn "Not Secure / Certificate Error" —
just tap Advanced → Proceed anyway. This is normal for self-signed certs.

Place server.py and index.html in the SAME folder.
"""

from flask import Flask, jsonify, request, send_file  # type: ignore
import requests  # type: ignore
import os, socket, tempfile, subprocess

app = Flask(__name__)

VEHICLE_API_BASE = "https://car-mix-fee-demo.vercel.app"
VEHICLE_API_KEY  = "DEMO"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@app.route("/")
def index():
    return send_file(os.path.join(BASE_DIR, "index.html"))

@app.route("/api/vehicle")
def vehicle():
    rc = request.args.get("rc", "").strip().upper()
    if not rc:
        return jsonify({"error": "rc parameter is required"}), 400

    url = f"{VEHICLE_API_BASE}/?rc={rc}&key={VEHICLE_API_KEY}"
    print(f"[VEHIQ] Fetching: {url}")
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
        print(f"[VEHIQ] openssl not found or failed: {e}")
        return None, None

if __name__ == "__main__":
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
  ║  Local :  https://localhost:5000                 ║
  ║  Mobile:  https://{local_ip}:5000
  ╠══════════════════════════════════════════════════╣
  ║  On mobile browser: tap Advanced → Proceed       ║
  ║  (cert warning is normal — camera WILL work!)    ║
  ╚══════════════════════════════════════════════════╝
        """)
        app.run(host="0.0.0.0", port=5000, debug=False,
                ssl_context=(cert_file, key_file))
    else:
        print(f"""
  ╔══════════════════════════════════════════════════╗
  ║           VEHIQ — VEHICLE INTELLIGENCE           ║
  ╠══════════════════════════════════════════════════╣
  ║  Local :  http://localhost:5000                  ║
  ║  Mobile:  http://{local_ip}:5000
  ╠══════════════════════════════════════════════════╣
  ║  ⚠ HTTP mode — camera scan won't work on mobile  ║
  ║  Install openssl to enable HTTPS automatically.  ║
  ╚══════════════════════════════════════════════════╝
        """)
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))