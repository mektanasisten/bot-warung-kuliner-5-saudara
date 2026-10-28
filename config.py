import os

# ==========================================
# KONFIGURASI UTAMA WARUNG KULINER PALEMBANG
# ==========================================

# Identitas Usaha
NAMA_WARUNG = os.getenv("NAMA_WARUNG", "Warung Kuliner Pempek & Tekwan Mama")
TAGLINE_WARUNG = os.getenv("TAGLINE_WARUNG", "Cita Rasa Asli Wong Kito Galo - Gurih, Asli Ikan Tenggiri, Cuko Kental Mantap")

# Nomor WhatsApp Orang Tua (Admin Dapur) untuk Menerima Notifikasi & Konfirmasi
# Format: Gunakan kode negara tanpa tanda plus atau awalan 08 (misal: 6281234567890)
NOMOR_WA_ORTU = os.getenv("NOMOR_WA_ORTU", "6281234567890")

# Opsi Pengiriman dan Ongkos Kirim Awal
ONGKIR_OPTIONS = {
    "1": {
        "nama": "Paket Ongkir 1 (Area Dekat / Radius s.d. 3 KM)",
        "biaya": 5000,
        "estimasi": "20 - 35 menit"
    },
    "2": {
        "nama": "Paket Ongkir 2 (Area Menengah / Radius 3 - 7 KM)",
        "biaya": 10000,
        "estimasi": "35 - 55 menit"
    }
}

# Provider WhatsApp Gateway
# Pilihan: 'fonnte' (cloud gateway sangat populer di Indonesia) atau 'mock' (mode uji coba lokal)
GATEWAY_PROVIDER = os.getenv("GATEWAY_PROVIDER", "fonnte")

# Token API WhatsApp Gateway (Didapatkan gratis dari dashboard Fonnte.com)
FONNTE_TOKEN = os.getenv("FONNTE_TOKEN", "ISI_DENGAN_TOKEN_FONNTE_ANDA")

# Link URL atau Path File Gambar QRIS Toko
# Jika di-host di Cloud, taruh gambar QRIS di folder static atau gunakan link hosting gambar (Imgur/Cloudinary)
QRIS_IMAGE_URL = os.getenv("QRIS_IMAGE_URL", "https://i.ibb.co/vzCq8wK/contoh-qris.jpg")
QRIS_LOCAL_PATH = os.path.join(os.path.dirname(__file__), "static", "qris.jpg")

# Informasi Rekening Alternatif (Jika pembeli kesulitan scan QRIS)
INFO_REKENING = """
Atau transfer manual ke:
Bank BCA: 1234-567-890 a.n. Pempek Mama
Bank Mandiri: 987-654-321 a.n. Pempek Mama
"""

# Path File Menu CSV
MENU_FILE_PATH = os.getenv("MENU_FILE_PATH", os.path.join(os.path.dirname(__file__), "menu.csv"))

# Path Database Pesanan (JSON sederhana agar tidak perlu install database berat)
ORDERS_DB_PATH = os.path.join(os.path.dirname(__file__), "orders_db.json")

# Konfigurasi Server Web
PORT = int(os.getenv("PORT", 5000))
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1")
SECRET_KEY = os.getenv("SECRET_KEY", "kunci_rahasia_warung_pempek_2026")
