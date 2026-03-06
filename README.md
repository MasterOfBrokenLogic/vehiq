# VEHIQ — Vehicle Intelligence Terminal

> Look up any Indian vehicle's owner details, contact number, insurance, RTO info and more — just by entering a registration number. Built with a terminal aesthetic.

---

## Features

- **Instant RC Lookup** — Enter any Indian vehicle registration number and get full owner details
- **Live Plate Scanner** — Point your camera at any number plate and it auto-detects, fills, and searches — no typing needed
- **Mobile Ready** — Fits your screen perfectly, no awkward scrolling until results load
- **Dark / Light Mode** — Toggle between themes
- **HTTPS by default** — Auto-generates a self-signed SSL cert so camera works on mobile
- **Multi-API aggregation** — Pulls data from multiple nodes for maximum result coverage
- **Cyberpunk terminal UI** — Built with Bebas Neue, Share Tech Mono, scan lines, glowing accents

---

## What It Shows

| Field | Details |
|-------|---------|
| Owner Name | Registered owner's full name |
| Father / Guardian | Father or guardian name |
| Mobile Number | Registered contact (if available) |
| Make / Model | Vehicle brand and model |
| Fuel Type | Petrol / Diesel / Electric / CNG |
| Color | Vehicle color |
| Engine & Chassis No. | Unique identifiers |
| Registration Date | Date of first registration |
| RTO | Registering RTO office |
| Insurance | Company name + expiry date |
| Fitness Upto | Fitness certificate validity |
| Financer | Loan/financer details |
| Address | Owner's registered address |

---

## Getting Started

### Prerequisites

- Python 3.7+
- `pip` package manager
- `openssl` (for HTTPS / mobile camera support)

### Installation

**1. Clone the repo**
```bash
git clone https://github.com/MasterOfBrokenLogic/vehiq.git
cd vehiq
```

**2. Install dependencies**
```bash
pip install flask requests
```

**3. Run the server**
```bash
python server.py
```

**4. Open in browser**
- On your PC: [https://localhost:5000](https://localhost:5000)
- On mobile (same Wi-Fi): `https://YOUR_PC_IP:5000`

> Your browser will show a **"Certificate Warning"** — this is normal for self-signed certs. Just tap **Advanced → Proceed** and everything works fine including the camera.

---

## Using the Plate Scanner

1. Open VEHIQ on your **mobile browser**
2. Tap the **scan icon** (top right of the input box)
3. Allow camera permission when prompted
4. **Point your camera at any vehicle's number plate**
5. The system auto-detects the number, fills it in, and searches — instantly

> Works best in good lighting. Hold the phone steady for 1–2 seconds.

---

## Project Structure

```
vehiq/
├── server.py       # Flask proxy server (handles API + HTTPS)
├── index.html      # Full frontend (single file, no build needed)
└── README.md       # You are here
```

---

## How It Works

```
User enters plate / scans via camera
        ↓
index.html sends request to /api/vehicle
        ↓
server.py proxies to PVT Vehicle API
        ↓
Response aggregated from multiple data nodes
        ↓
Results rendered in the terminal UI
```

The Flask server acts as a proxy to avoid CORS issues and to keep the API key server-side. HTTPS is auto-enabled via a self-signed certificate generated at startup using `openssl`.

---

## Tips

- Supports all Indian RC formats: `KL41V2354`, `MH12AB1234`, `DL1CAA1234`
- 3-digit serial numbers are auto-padded to 4 digits
- If the phone number isn't shown, the owner hasn't registered a mobile with the RTO
- Camera scanner uses [Tesseract.js](https://github.com/naptha/tesseract.js) for in-browser OCR — no data leaves your device during scanning

---

## Built With

- [Flask](https://flask.palletsprojects.com/) — Python web framework
- [Tesseract.js](https://github.com/naptha/tesseract.js) — In-browser OCR for plate scanning
- [Bebas Neue](https://fonts.google.com/specimen/Bebas+Neue) + [Share Tech Mono](https://fonts.google.com/specimen/Share+Tech+Mono) + [Rajdhani](https://fonts.google.com/specimen/Rajdhani) — Fonts
- Vanilla JS + CSS — No frontend framework, no build step

---

## Creator

**@4nsil!**
- Telegram: [@drazeforce](https://t.me/drazeforce)

---

## Disclaimer

This tool is intended for **informational and educational purposes only**. Vehicle registration data is sourced from publicly accessible government databases. Do not use this tool for any illegal, unethical, or privacy-violating purposes. The creator is not responsible for any misuse.

---

## License

This project is open source. Feel free to fork, modify, and build on it, just give credit :)

---

<div align="center">
  <sub>Built with ♥ by <a href="https://t.me/drazeforce">4nsil!</a></sub>
</div>
