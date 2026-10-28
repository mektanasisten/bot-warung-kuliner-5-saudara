from flask import Flask, request, jsonify, render_template_string
import os
import logging
import config
from bot_engine import BotEngine

# Inisialisasi Flask & Logging
app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("WebApp")

# Inisialisasi Bot Engine
bot = BotEngine()

# Template HTML Dashboard Bersih untuk Tampilan Web
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Server Bot WhatsApp - {{ warung_name }}</title>
    <style>
        :root {
            --primary: #c94a29;
            --primary-dark: #a3381b;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text-main: #1e293b;
            --text-muted: #64748b;
            --border: #e2e8f0;
            --success: #16a34a;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: var(--bg);
            color: var(--text-main);
            margin: 0;
            padding: 24px;
            line-height: 1.6;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
        }
        .header {
            background: var(--card-bg);
            padding: 28px;
            border-radius: 16px;
            border: 1px solid var(--border);
            margin-bottom: 24px;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
        }
        .badge {
            display: inline-block;
            background: #dcfce7;
            color: #15803d;
            padding: 4px 12px;
            border-radius: 9999px;
            font-size: 13px;
            font-weight: 600;
            margin-bottom: 12px;
        }
        h1 { margin: 0 0 8px 0; color: var(--primary); font-size: 26px; }
        .tagline { color: var(--text-muted); font-size: 15px; margin: 0; }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 18px;
            margin-bottom: 24px;
        }
        .card {
            background: var(--card-bg);
            padding: 20px;
            border-radius: 12px;
            border: 1px solid var(--border);
        }
        .card h3 { margin: 0 0 10px 0; font-size: 16px; color: var(--text-muted); }
        .card .value { font-size: 28px; font-weight: 700; color: var(--text-main); }
        .simulator {
            background: var(--card-bg);
            padding: 24px;
            border-radius: 16px;
            border: 1px solid var(--border);
            margin-bottom: 24px;
        }
        .simulator h2 { margin-top: 0; font-size: 20px; color: var(--primary); }
        .form-group { margin-bottom: 14px; }
        label { display: block; font-weight: 600; font-size: 14px; margin-bottom: 6px; }
        input, select, textarea {
            width: 100%;
            padding: 10px 14px;
            border: 1px solid var(--border);
            border-radius: 8px;
            font-size: 15px;
            box-sizing: border-box;
        }
        button {
            background: var(--primary);
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            font-size: 15px;
        }
        button:hover { background: var(--primary-dark); }
        .chat-box {
            background: #f1f5f9;
            padding: 16px;
            border-radius: 8px;
            border: 1px solid var(--border);
            margin-top: 16px;
            white-space: pre-wrap;
            font-family: monospace;
            font-size: 14px;
            max-height: 350px;
            overflow-y: auto;
        }
        .footer {
            text-align: center;
            font-size: 13px;
            color: var(--text-muted);
            margin-top: 30px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <span class="badge">● Sistem Berjalan Aktif</span>
            <h1>{{ warung_name }}</h1>
            <p class="tagline">{{ tagline }}</p>
        </div>

        <div class="grid">
            <div class="card">
                <h3>Total Menu Aktif</h3>
                <div class="value">{{ total_menu }}</div>
                <small style="color: var(--text-muted);">Dimuat dari file menu.csv</small>
            </div>
            <div class="card">
                <h3>Antrean Konfirmasi Dapur</h3>
                <div class="value" style="color: #ea580c;">{{ pending_kitchen }}</div>
                <small style="color: var(--text-muted);">Menunggu balasan WhatsApp Mama/Papa</small>
            </div>
            <div class="card">
                <h3>Total Seluruh Pesanan</h3>
                <div class="value">{{ total_orders }}</div>
                <small style="color: var(--text-muted);">Tercatat di sistem</small>
            </div>
        </div>

        <div class="simulator">
            <h2>🧪 Simulator Interaksi Chatbot</h2>
            <p style="color: var(--text-muted); font-size: 14px;">
                Coba langsung percakapan di sini tanpa perlu menghubungkan ke WhatsApp terlebih dahulu.
            </p>
            <div class="form-group">
                <label>Pilih Peran Pengirim:</label>
                <select id="simSender">
                    <option value="6289988776655">Pembeli (Customer: 089988776655)</option>
                    <option value="{{ admin_phone }}">Orang Tua (Admin Dapur: {{ admin_phone }})</option>
                </select>
            </div>
            <div class="form-group">
                <label>Pesan Masuk:</label>
                <input type="text" id="simMessage" placeholder="Contoh: halo, menu, 1 x 2, lanjut, 1, dll." value="halo">
            </div>
            <button onclick="sendSimulatedMessage()">Kirim Pesan Uji Coba</button>

            <div id="simResult" class="chat-box" style="display:none;"></div>
        </div>

        <div class="card">
            <h3>URL Webhook untuk WhatsApp Gateway</h3>
            <p style="font-size: 14px; color: var(--text-muted);">
                Salin tautan ini dan masukkan ke kolom Webhook di dashboard WhatsApp Gateway Anda (misal Fonnte):
            </p>
            <code style="display:block; background:#f1f5f9; padding:10px; border-radius:6px; font-weight:bold;">
                {{ host_url }}webhook
            </code>
        </div>

        <div class="footer">
            Sistem Otomasi Chatbot WhatsApp Kuliner Palembang &copy; 2026. Dirancang khusus mudah digunakan orang tua lansia.
        </div>
    </div>

    <script>
        async function sendSimulatedMessage() {
            const sender = document.getElementById('simSender').value;
            const message = document.getElementById('simMessage').value;
            const resultBox = document.getElementById('simResult');

            resultBox.style.display = 'block';
            resultBox.textContent = 'Memproses balasan bot...';

            try {
                const res = await fetch('/simulate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ sender: sender, message: message })
                });
                const data = await res.json();
                resultBox.textContent = '🤖 BALASAN CHATBOT:\\n\\n' + data.reply;
            } catch (err) {
                resultBox.textContent = 'Gagal menghubungi server: ' + err.message;
            }
        }
    </script>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    """Halaman Dashboard Utama untuk memantau status sistem dan simulasi."""
    menus = bot.menu_manager.get_all()
    orders = bot.order_manager.orders
    pending_queue = bot.order_manager.pending_kitchen_queue
    host_url = request.host_url

    return render_template_string(
        DASHBOARD_HTML,
        warung_name=config.NAMA_WARUNG,
        tagline=config.TAGLINE_WARUNG,
        admin_phone=config.NOMOR_WA_ORTU,
        total_menu=len(menus),
        pending_kitchen=len(pending_queue),
        total_orders=len(orders),
        host_url=host_url
    )

@app.route("/webhook", methods=["POST"])
def webhook():
    """
    Endpoint Penerima Webhook dari WhatsApp Gateway (Fonnte, WAHA, dll).
    Menerima data JSON maupun Form Data secara fleksibel.
    """
    sender = None
    message = None
    media_url = None

    # 1. Coba baca dari format JSON
    if request.is_json:
        data = request.get_json(silent=True) or {}
        sender = data.get("sender") or data.get("from") or data.get("phone")
        message = data.get("message") or data.get("text") or data.get("body")
        media_url = data.get("url") or data.get("media")

    # 2. Coba baca dari Form Data (standar Fonnte Webhook)
    if not sender and request.form:
        sender = request.form.get("sender") or request.form.get("from") or request.form.get("phone")
        message = request.form.get("message") or request.form.get("text")
        media_url = request.form.get("url")

    if not sender:
        logger.warning(f"Webhook diterima tanpa pengirim: {request.data}")
        return jsonify({"status": "ignored", "reason": "No sender"}), 200

    logger.info(f"Pesan webhook diterima dari {sender}: {message}")

    # Eksekusi logika bot
    reply = bot.handle_incoming_message(sender, message, media_url)

    # Kembalikan response JSON (beberapa gateway mendukung balasan langsung dari response HTTP)
    return jsonify({
        "status": "success",
        "sender": sender,
        "reply": reply
    }), 200

@app.route("/simulate", methods=["POST"])
def simulate():
    """Endpoint untuk mencoba pesan melalui simulator web."""
    data = request.get_json(silent=True) or {}
    sender = data.get("sender", "6289988776655")
    message = data.get("message", "halo")
    media_url = data.get("url")

    reply = bot.handle_incoming_message(sender, message, media_url)
    return jsonify({
        "status": "success",
        "sender": sender,
        "message": message,
        "reply": reply
    })

@app.route("/menu", methods=["GET"])
def get_menu():
    """API untuk melihat seluruh daftar menu yang aktif saat ini."""
    menus = bot.menu_manager.get_all()
    return jsonify({
        "warung": config.NAMA_WARUNG,
        "total": len(menus),
        "data": menus
    })

@app.route("/orders", methods=["GET"])
def get_orders():
    """API untuk melihat daftar seluruh pesanan."""
    return jsonify({
        "orders": bot.order_manager.orders,
        "pending_kitchen_queue": bot.order_manager.pending_kitchen_queue
    })

if __name__ == "__main__":
    print(f"Menjalankan server {config.NAMA_WARUNG} di port {config.PORT}...")
    app.run(host="0.0.0.0", port=config.PORT, debug=config.DEBUG)
