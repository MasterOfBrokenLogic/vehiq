#!/usr/bin/env python3
"""
VEHIQ — Vehicle lookup proxy server

Local:  python server.py  → http://localhost:5000
Render: auto-detects PORT env variable, no SSL needed (Render handles HTTPS)
"""

from flask import Flask, jsonify, request, send_file  # type: ignore
import requests  # type: ignore
import os, socket, tempfile, subprocess, hmac, hashlib, secrets, time

app = Flask(__name__)

# ── Obfuscated config (XOR encoded) ──────────────────────────────────────────
_K = [110,135,149,142,52,192,80,195,80,96,177,51,172,149,118,200]
_B = [6,243,225,254,71,250,127,236,51,1,195,30,193,252,14,229,8,226,240,163,80,165,61,172,126,22,212,65,207,240,26,230,15,247,229]
_A = [42,194,216,193]
_d = lambda v: ''.join(chr(c ^ _K[i % len(_K)]) for i, c in enumerate(v))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Server-side admin credentials (never sent to browser) ────────────────────
# Admin username + password stored as SHA-256 hashes only
# To change: run in terminal:
#   python3 -c "import hashlib; print(hashlib.sha256(b'yourpassword').hexdigest())"
# Then set ADMIN_USER_HASH and ADMIN_PASS_HASH as Render environment variables.
# Falls back to these defaults if env vars not set — CHANGE THESE in production!
_AU = [24,226,253,231,69,161,52,174,57,14]   # "vehiqadmin" xor _K
_AP = [56,194,221,175,101,128,100,167,61,81,223,16,158,165,68,253]  # "VEH!Q@4dm1n#2025" xor _K
ADMIN_USERNAME = _d(_AU)
ADMIN_PASSWORD = _d(_AP)

ADMIN_USER_HASH = os.environ.get(
    'ADMIN_USER_HASH',
    hashlib.sha256(ADMIN_USERNAME.encode()).hexdigest()
)
ADMIN_PASS_HASH = os.environ.get(
    'ADMIN_PASS_HASH',
    hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()
)

# ── Token signing secret (set ADMIN_SECRET env var on Render) ────────────────
TOKEN_SECRET = os.environ.get('ADMIN_SECRET', secrets.token_hex(32))
# NOTE: if ADMIN_SECRET is not set, tokens invalidate on every server restart.
# Set it as a fixed env var on Render to persist across deploys.

TOKEN_TTL = 60 * 60 * 8  # 8 hours

# In-memory revoked tokens (cleared on restart — acceptable for admin sessions)
_revoked = set()

def _make_token():
    """Generate a time-limited HMAC-signed admin token."""
    exp = int(time.time()) + TOKEN_TTL
    payload = f"admin:{exp}"
    sig = hmac.new(TOKEN_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{sig}"

def _verify_token(token):
    """Returns True if token is valid, unexpired, and not revoked."""
    if not token or token in _revoked:
        return False
    try:
        parts = token.split(":")
        if len(parts) != 3 or parts[0] != "admin":
            return False
        exp = int(parts[1])
        sig = parts[2]
        payload = f"admin:{exp}"
        expected = hmac.new(TOKEN_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return False
        if time.time() > exp:
            return False
        return True
    except Exception:
        return False

def _require_admin():
    """Returns (True, None) or (False, error_response)."""
    token = request.headers.get('X-Admin-Token') or request.args.get('t')
    if not _verify_token(token):
        return False, (jsonify({'error': 'Unauthorized'}), 401)
    return True, None

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_file(os.path.join(BASE_DIR, "index.html"))

@app.route("/login.html")
def login_page():
    return send_file(os.path.join(BASE_DIR, "login.html"))

@app.route("/admin.html")
def admin_page():
    """Serve admin page — actual auth enforced by /api/admin/verify on load."""
    return send_file(os.path.join(BASE_DIR, "admin.html"))

# ── Admin Auth API ────────────────────────────────────────────────────────────

@app.route("/api/admin/login", methods=["POST"])
def admin_login():
    data     = request.get_json(silent=True) or {}
    username = data.get("username", "").strip().lower()
    password = data.get("password", "")

    u_hash = hashlib.sha256(username.encode()).hexdigest()
    p_hash = hashlib.sha256(password.encode()).hexdigest()

    # Constant-time compare — prevents timing attacks
    u_ok = hmac.compare_digest(u_hash, ADMIN_USER_HASH)
    p_ok = hmac.compare_digest(p_hash, ADMIN_PASS_HASH)

    if u_ok and p_ok:
        token = _make_token()
        print("[VEHIQ] Admin login success")
        return jsonify({"token": token})
    else:
        print("[VEHIQ] Admin login failed")
        return jsonify({"error": "Invalid credentials"}), 401

@app.route("/api/admin/verify", methods=["GET"])
def admin_verify():
    """Frontend calls this on every admin page load to validate token."""
    ok, err = _require_admin()
    if not ok:
        return err
    return jsonify({"valid": True})

@app.route("/api/admin/logout", methods=["POST"])
def admin_logout():
    token = request.headers.get('X-Admin-Token')
    if token:
        _revoked.add(token)
    return jsonify({"ok": True})

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
  ║  Local :  https://localhost:{port}                   ║
  ║  Mobile:  https://{local_ip}:{port}
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
  ║  Local :  http://localhost:{port}                    ║
  ║  Mobile:  http://{local_ip}:{port}
  ╠══════════════════════════════════════════════════╣
  ║  HTTP mode — camera won't work on mobile         ║
  ║  Install openssl to enable HTTPS locally.        ║
  ╚══════════════════════════════════════════════════╝
            """)
            app.run(host="0.0.0.0", port=port, debug=False)