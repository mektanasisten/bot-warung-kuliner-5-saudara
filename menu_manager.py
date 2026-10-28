import csv
import os
import re

class MenuManager:
    def __init__(self, csv_path):
        self.csv_path = csv_path
        self.menus = []
        self.load_menu()

    def load_menu(self):
        """Membaca file menu.csv dan memuatnya ke memori sistem."""
        self.menus = []
        if not os.path.exists(self.csv_path):
            return

        with open(self.csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Hanya muat menu yang ditandai '1' (tersedia)
                if row.get("tersedia", "1").strip() == "1":
                    self.menus.append({
                        "kode": row.get("kode", "").strip(),
                        "kategori": row.get("kategori", "").strip(),
                        "nama": row.get("nama", "").strip(),
                        "harga": int(row.get("harga", 0)),
                        "satuan": row.get("satuan", "porsi").strip(),
                        "deskripsi": row.get("deskripsi", "").strip(),
                        "tersedia": True
                    })

    def get_all(self):
        """Mengembalikan semua menu yang aktif."""
        self.load_menu() # Reload agar perubahan manual di Excel langsung terdeteksi
        return self.menus

    def get_by_code(self, kode):
        """Mencari menu berdasarkan kode unik (misal: 1, 2, P1, dll)."""
        self.load_menu()
        kode_clean = str(kode).strip().upper()
        for item in self.menus:
            if item["kode"].upper() == kode_clean:
                return item
        return None

    def format_menu_whatsapp(self, nama_warung, tagline):
        """
        Menghasilkan teks menu yang rapi, elegan, dan mudah dibaca di WhatsApp.
        Dikelompokkan rapi per kategori (Paket, Pempek Satuan, Tekwan/Model, Minuman).
        """
        self.load_menu()
        if not self.menus:
            return "Daftar menu sedang diperbarui. Silakan hubungi langsung admin ya Kak."

        # Kelompokkan per kategori
        kategori_dict = {}
        for item in self.menus:
            kat = item["kategori"]
            if kat not in kategori_dict:
                kategori_dict[kat] = []
            kategori_dict[kat].append(item)

        lines = [
            f"✨ *DAFTAR MENU {nama_warung.upper()}* ✨",
            f"_{tagline}_\n",
            "Halo Kak! Silakan pilih menu khas Palembang favorit Kakak di bawah ini:\n"
        ]

        # Prioritas urutan kategori
        urutan_prioritas = ["Paket", "Satuan", "Minuman"]
        all_categories = list(kategori_dict.keys())
        sorted_cats = [c for c in urutan_prioritas if c in all_categories] + [c for c in all_categories if c not in urutan_prioritas]

        for kat in sorted_cats:
            lines.append(f"━━━━━━━━━━━━━━━━━━━")
            lines.append(f"📌 *KATEGORI: {kat.upper()}*")
            lines.append(f"━━━━━━━━━━━━━━━━━━━")
            for item in kategori_dict[kat]:
                kode_display = f"[{item['kode']}]"
                harga_formatted = f"Rp {item['harga']:,}".replace(",", ".")
                lines.append(f"👉 *{kode_display} {item['nama']}*")
                lines.append(f"   Harga: *{harga_formatted}* / {item['satuan']}")
                if item["deskripsi"]:
                    lines.append(f"   _{item['deskripsi']}_")
                lines.append("")

        lines.append("━━━━━━━━━━━━━━━━━━━")
        lines.append("📝 *CARA PEMESANAN SANGAT MUDAH:*")
        lines.append("Cukup ketik *KODE MENU* dan *JUMLAHNYA*.")
        lines.append("Contoh: *1 x 2, 2 x 5, P1 x 1*")
        lines.append("Atau ketik kodenya saja jika pesan 1 buah, contoh: *P1* atau *1*")
        lines.append("━━━━━━━━━━━━━━━━━━━")
        return "\n".join(lines)

    def parse_order_input(self, text):
        """
        Menganalisis teks pesanan pelanggan secara fleksibel.
        Bisa mendeteksi pola:
        - '1 x 2, 2 x 5, P1 x 1'
        - '1:2, 2:5'
        - '1 2 pcs, P1 1 paket'
        - '1, 2, 7' (masing-masing 1)
        - 'P1'
        Mengembalikan tuple: (list_item_tervalidasi, list_kode_tidak_dikenal)
        """
        self.load_menu()
        items_ordered = []
        unknown_codes = []

        # Pisahkan berdasarkan koma atau baris baru
        parts = re.split(r"[,;\n]+", text.strip())

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Pola 1: KODE x JUMLAH (contoh: 1 x 3 atau P1*2 atau 1:3 atau 1 3pcs)
            match_mult = re.search(r"^([a-zA-Z0-9]+)\s*(?:[xX*:]|\s+)\s*(\d+)", part)
            if match_mult:
                kode = match_mult.group(1).upper()
                qty = int(match_mult.group(2))
            else:
                # Pola 2: Hanya KODE (contoh: 1 atau P1 atau P2)
                match_single = re.search(r"^([a-zA-Z0-9]+)$", part)
                if match_single:
                    kode = match_single.group(1).upper()
                    qty = 1
                else:
                    # Coba ambil karakter pertama kata
                    words = part.split()
                    if words:
                        kode = words[0].upper()
                        qty = 1
                    else:
                        continue

            menu_item = self.get_by_code(kode)
            if menu_item:
                subtotal = menu_item["harga"] * qty
                items_ordered.append({
                    "kode": menu_item["kode"],
                    "nama": menu_item["nama"],
                    "harga": menu_item["harga"],
                    "qty": qty,
                    "satuan": menu_item["satuan"],
                    "subtotal": subtotal
                })
            else:
                unknown_codes.append(kode)

        return items_ordered, unknown_codes
