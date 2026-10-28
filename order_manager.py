import json
import os
import time
from datetime import datetime

class OrderManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.orders = {}
        self.customer_sessions = {}
        self.pending_kitchen_queue = []
        self.load_db()

    def load_db(self):
        """Memuat database pesanan dari file JSON."""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.orders = data.get("orders", {})
                    self.pending_kitchen_queue = data.get("pending_kitchen_queue", [])
            except Exception:
                self.orders = {}
                self.pending_kitchen_queue = []
        else:
            self.orders = {}
            self.pending_kitchen_queue = []

    def save_db(self):
        """Menyimpan data pesanan ke file JSON."""
        data = {
            "orders": self.orders,
            "pending_kitchen_queue": self.pending_kitchen_queue,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def generate_order_id(self):
        """Menghasilkan nomor unik pesanan ramah manusia, contoh: #PK-101."""
        count = len(self.orders) + 1
        return f"#PK-{count:03d}"

    def get_or_create_session(self, phone):
        """Mendapatkan sesi percakapan aktif dari nomor pembeli."""
        if phone not in self.customer_sessions:
            self.customer_sessions[phone] = {
                "phone": phone,
                "state": "IDLE",
                "cart": [],
                "delivery_type": None,
                "ongkir": 0,
                "nama_pembeli": "",
                "alamat_pembeli": "",
                "current_order_id": None,
                "last_active": time.time()
            }
        else:
            self.customer_sessions[phone]["last_active"] = time.time()
        return self.customer_sessions[phone]

    def reset_session(self, phone):
        """Mereset keranjang dan sesi pelanggan untuk pesanan baru."""
        self.customer_sessions[phone] = {
            "phone": phone,
            "state": "IDLE",
            "cart": [],
            "delivery_type": None,
            "ongkir": 0,
            "nama_pembeli": "",
            "alamat_pembeli": "",
            "current_order_id": None,
            "last_active": time.time()
        }

    def add_to_cart(self, phone, items):
        """Menambahkan menu ke keranjang belanja pelanggan."""
        session = self.get_or_create_session(phone)
        for new_item in items:
            # Cek apakah menu sudah ada di keranjang, jika ada tambahkan jumlahnya
            found = False
            for existing in session["cart"]:
                if existing["kode"] == new_item["kode"]:
                    existing["qty"] += new_item["qty"]
                    existing["subtotal"] = existing["harga"] * existing["qty"]
                    found = True
                    break
            if not found:
                session["cart"].append(new_item)

    def calculate_totals(self, cart, ongkir=0):
        """Menghitung total harga makanan, ongkir, dan total akhir."""
        total_makanan = sum(item["subtotal"] for item in cart)
        grand_total = total_makanan + ongkir
        return total_makanan, grand_total

    def create_pending_order(self, phone):
        """Mencatat pesanan resmi yang siap dikonfirmasi ke dapur orang tua."""
        session = self.get_or_create_session(phone)
        order_id = self.generate_order_id()
        total_makanan, grand_total = self.calculate_totals(session["cart"], session["ongkir"])

        order_data = {
            "order_id": order_id,
            "phone": phone,
            "nama_pembeli": session["nama_pembeli"],
            "alamat_pembeli": session["alamat_pembeli"],
            "delivery_type": session["delivery_type"],
            "items": list(session["cart"]),
            "total_makanan": total_makanan,
            "ongkir": session["ongkir"],
            "grand_total": grand_total,
            "status": "WAITING_KITCHEN",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        self.orders[order_id] = order_data
        session["current_order_id"] = order_id
        session["state"] = "WAITING_KITCHEN"

        # Masukkan ke antrean dapur
        if order_id not in self.pending_kitchen_queue:
            self.pending_kitchen_queue.append(order_id)

        self.save_db()
        return order_data

    def get_latest_pending_kitchen_order(self):
        """Mendapatkan pesanan paling baru yang sedang menunggu persetujuan dapur."""
        if not self.pending_kitchen_queue:
            return None
        # Ambil pesanan terakhir yang belum diproses
        latest_id = self.pending_kitchen_queue[-1]
        return self.orders.get(latest_id)

    def update_order_status(self, order_id, new_status):
        """Memperbarui status pesanan (CONFIRMED_READY, REJECTED, PAID, COMPLETED)."""
        if order_id in self.orders:
            self.orders[order_id]["status"] = new_status
            if order_id in self.pending_kitchen_queue and new_status in ["CONFIRMED_READY", "REJECTED"]:
                self.pending_kitchen_queue.remove(order_id)
            self.save_db()
            return True
        return False
