import logging
import re
import config
from gateway_adapter import WhatsAppGateway
from menu_manager import MenuManager
from order_manager import OrderManager

logger = logging.getLogger("BotEngine")

class BotEngine:
    def __init__(self):
        self.gateway = WhatsAppGateway()
        self.menu_manager = MenuManager(config.MENU_FILE_PATH)
        self.order_manager = OrderManager(config.ORDERS_DB_PATH)
        self.admin_phone = self.gateway.clean_phone_number(config.NOMOR_WA_ORTU)

    def handle_incoming_message(self, sender_phone, message_text, media_url=None):
        """
        Titik masuk utama untuk memproses semua pesan WhatsApp yang masuk.
        Membedakan apakah pengirim adalah Orang Tua (Admin Dapur) atau Pembeli.
        """
        clean_sender = self.gateway.clean_phone_number(sender_phone)
        text = str(message_text).strip() if message_text else ""

        logger.info(f"Pesan masuk dari {clean_sender}: '{text}' (media: {bool(media_url)})")

        # 1. CEK APAKAH INI PESAN DARI ORANG TUA (ADMIN DAPUR)
        if clean_sender == self.admin_phone:
            return self.handle_admin_message(clean_sender, text, media_url)

        # 2. JIKA BUKAN ADMIN, INI ADALAH PESAN DARI PEMBELI (CUSTOMER)
        return self.handle_customer_message(clean_sender, text, media_url)

    # =========================================================================
    # ALUR KHUSUS ORANG TUA / ADMIN DAPUR (SANGAT MUDAH & RAMAH LANSIA)
    # =========================================================================
    def handle_admin_message(self, admin_phone, text, media_url=None):
        """
        Memproses instruksi dari orang tua melalui chat WhatsApp.
        Cukup balas angka '1' (Ready) atau '2' (Habis).
        """
        text_upper = text.upper().strip()

        # Konfirmasi READY (Ketik 1)
        if text_upper.startswith("1"):
            # Cek apakah ada nomor order spesifik (misal: "1 PK-101" atau cukup "1")
            parts = text_upper.split()
            target_order = None
            if len(parts) > 1:
                target_order_id = parts[1]
                if not target_order_id.startswith("#"):
                    target_order_id = "#" + target_order_id
                target_order = self.order_manager.orders.get(target_order_id)

            if not target_order:
                target_order = self.order_manager.get_latest_pending_kitchen_order()

            if not target_order:
                msg = "Halo Mama/Papa, saat ini *tidak ada pesanan baru* yang menunggu konfirmasi dapur."
                self.gateway.send_text(admin_phone, msg)
                return msg

            order_id = target_order["order_id"]
            cust_phone = target_order["phone"]
            cust_name = target_order["nama_pembeli"]
            grand_total_fmt = f"Rp {target_order['grand_total']:,}".replace(",", ".")

            # 1. Update status pesanan
            self.order_manager.update_order_status(order_id, "CONFIRMED_READY")

            # 2. Kirim pesan konfirmasi ke nomor pembeli
            cust_msg = [
                f"Kabar gembira Kak {cust_name}! 🍽️✨",
                f"Dapur kami mengonfirmasi pesanan Kakak (*{order_id}*) *SIAP DIBUATKAN!*",
                "",
                f"Total Pembayaran: *{grand_total_fmt}*",
                "",
                "Silakan lakukan pembayaran via *QRIS* pada gambar di bawah ini ya Kak.",
                "Setelah berhasil transfer, mohon kirimkan foto bukti transfer ke chat ini.",
                config.INFO_REKENING.strip(),
                "",
                "Terima kasih banyak Kak! Tim dapur kami mulai menyiapkan pesanan Kakak. 🙏"
            ]
            self.gateway.send_text(cust_phone, "\n".join(cust_msg))

            # 3. Kirim gambar QRIS ke pembeli
            qris_caption = f"Scan QRIS ini untuk pembayaran pesanan {order_id} sebesar {grand_total_fmt} a.n. {config.NAMA_WARUNG}"
            self.gateway.send_image(cust_phone, config.QRIS_IMAGE_URL, qris_caption)

            # 4. Berikan feedback ke orang tua bahwa sistem sudah membalas pembeli
            admin_feedback = (
                f"✅ *PESANAN {order_id} BERHASIL DIKONFIRMASI READY!*\n\n"
                f"Pembeli ({cust_name}) sudah otomatis menerima rincian bayar dan gambar QRIS.\n"
                f"Silakan mulai memasak/menyiapkan pesanan ini ya Mama/Papa. Semangat! ❤️"
            )
            self.gateway.send_text(admin_phone, admin_feedback)
            return admin_feedback

        # Konfirmasi BAHAN HABIS / TOLAK (Ketik 2)
        elif text_upper.startswith("2"):
            parts = text_upper.split()
            target_order = None
            if len(parts) > 1:
                target_order_id = parts[1]
                if not target_order_id.startswith("#"):
                    target_order_id = "#" + target_order_id
                target_order = self.order_manager.orders.get(target_order_id)

            if not target_order:
                target_order = self.order_manager.get_latest_pending_kitchen_order()

            if not target_order:
                msg = "Halo Mama/Papa, saat ini *tidak ada pesanan* yang perlu dibatalkan."
                self.gateway.send_text(admin_phone, msg)
                return msg

            order_id = target_order["order_id"]
            cust_phone = target_order["phone"]
            cust_name = target_order["nama_pembeli"]

            self.order_manager.update_order_status(order_id, "REJECTED")

            # Beritahu pembeli dengan santun
            cust_msg = (
                f"Mohon maaf yang sebesar-besarnya Kak {cust_name}. 🙏\n\n"
                f"Dapur kami mengabarkan bahwa stok bahan untuk pesanan (*{order_id}*) saat ini sedang habis atau pesanan dapur sedang penuh kuota hari ini.\n\n"
                f"Pesanan Kakak belum dapat kami proses saat ini. Semoga bisa menikmati hidangan kami di kesempatan berikutnya ya Kak. Terima kasih banyak atas pengertiannya! ❤️"
            )
            self.gateway.send_text(cust_phone, cust_msg)

            admin_feedback = (
                f"❌ *PESANAN {order_id} TELAH DIBATALKAN.*\n"
                f"Pembeli ({cust_name}) sudah kami beri tahu dengan sangat sopan."
            )
            self.gateway.send_text(admin_phone, admin_feedback)
            return admin_feedback

        # Perintah Bantuan / Cek Status untuk Admin
        elif text_upper in ["CEK", "STATUS", "ANTREAN"]:
            queue = self.order_manager.pending_kitchen_queue
            if not queue:
                msg = "Saat ini tidak ada antrean pesanan baru yang menunggu konfirmasi dapur."
            else:
                msg = f"📋 *DAFTAR PESANAN MENUNGGU KONFIRMASI ({len(queue)} pesanan):*\n"
                for o_id in queue:
                    ord_item = self.order_manager.orders.get(o_id, {})
                    msg += f"- *{o_id}* a.n. {ord_item.get('nama_pembeli')} (Rp {ord_item.get('grand_total', 0):,})\n"
                msg += "\nBalas *1* untuk konfirmasi Ready pesanan terbaru, atau *2* jika habis."
            self.gateway.send_text(admin_phone, msg)
            return msg

        # Pesan bantuan umum jika orang tua mengetik hal lain
        else:
            help_msg = (
                f"Halo Mama/Papa pengelola {config.NAMA_WARUNG}! 👩‍🍳\n\n"
                "Panduan balasan sangat mudah:\n"
                "- Balas *1* jika bahan/dapur READY (Kirim QRIS ke pembeli)\n"
                "- Balas *2* jika bahan HABIS / Dapur tutup\n"
                "- Ketik *CEK* untuk melihat pesanan yang sedang antre"
            )
            self.gateway.send_text(admin_phone, help_msg)
            return help_msg

    # =========================================================================
    # ALUR INTERAKSI DENGAN PEMBELI (CUSTOMER CHAT FLOW)
    # =========================================================================
    def handle_customer_message(self, phone, text, media_url=None):
        """Memproses alur percakapan pembeli secara bertahap dan ramah."""
        session = self.order_manager.get_or_create_session(phone)
        state = session["state"]
        text_clean = text.strip()
        text_upper = text_clean.upper()

        # Deteksi bukti pembayaran berupa gambar
        if media_url or "BUKTI" in text_upper or "SUDAH BAYAR" in text_upper or "SUDAH TRANSFER" in text_upper:
            order_id = session.get("current_order_id") or "Pesanan Anda"
            reply = (
                f"Terima kasih banyak Kak! Bukti pembayaran untuk *{order_id}* sudah kami terima. 👍\n"
                f"Tim kami sedang menyiapkan pesanan Kakak dengan sepenuh hati. "
                f"Pesanan akan segera dikabari jika sudah siap diambil atau dalam perjalanan kurir! 🛵💨"
            )
            self.gateway.send_text(phone, reply)

            # Teruskan notifikasi pembayaran ke orang tua
            admin_notif = (
                f"💰 *BUKTI PEMBAYARAN MASUK!*\n"
                f"Pesanan: *{order_id}*\n"
                f"Pembeli: {session.get('nama_pembeli', 'Pelanggan')} ({phone})\n"
                f"Mohon cek mutasi rekening/QRIS dan segera siapkan makanan."
            )
            self.gateway.send_text(self.admin_phone, admin_notif)
            if media_url:
                self.gateway.send_image(self.admin_phone, media_url, f"Bukti Bayar {order_id}")
            return reply

        # Perintah BATAL / RESET
        if text_upper in ["BATAL", "RESET", "ULANG"]:
            self.order_manager.reset_session(phone)
            reply = "Keranjang dan pesanan Kakak telah direset. Mau pesan apa hari ini Kak? Ketik *MENU* untuk melihat daftar hidangan kami."
            self.gateway.send_text(phone, reply)
            return reply

        # Perintah BANTUAN
        if text_upper in ["BANTUAN", "HELP", "ADMIN"]:
            reply = (
                f"Halo Kak! Butuh bantuan langsung dari pemilik {config.NAMA_WARUNG}?\n"
                f"Silakan hubungi WhatsApp nomor dapur kami: {config.NOMOR_WA_ORTU}\n\n"
                f"Atau ketik *MENU* untuk kembali memilih hidangan lezat khas Palembang."
            )
            self.gateway.send_text(phone, reply)
            return reply

        # Salam pembuka atau ketik MENU
        salam_keywords = ["HALO", "HAI", "P", "MENU", "PESAN", "ORDER", "ASSALAMUALAIKUM", "PAGI", "SIANG", "SORE", "MALAM"]
        if state == "IDLE" or text_upper in salam_keywords:
            session["state"] = "SELECTING_MENU"
            menu_text = self.menu_manager.format_menu_whatsapp(config.NAMA_WARUNG, config.TAGLINE_WARUNG)
            self.gateway.send_text(phone, menu_text)
            return menu_text

        # TAHAP 1: PEMBELI SEDANG MEMILIH MENU
        if state == "SELECTING_MENU":
            # Jika pembeli ketik LANJUT padahal keranjang belum ada
            if text_upper == "LANJUT":
                if not session["cart"]:
                    reply = "Keranjang Kakak masih kosong. Silakan ketik kode menu yang ingin dipesan terlebih dahulu ya Kak (contoh: *1 x 2* atau *P1*)."
                    self.gateway.send_text(phone, reply)
                    return reply
                else:
                    # Lanjut ke tahap pemilihan delivery
                    session["state"] = "SELECTING_DELIVERY"
                    delivery_msg = self.format_delivery_options()
                    self.gateway.send_text(phone, delivery_msg)
                    return delivery_msg

            if text_upper == "TAMBAH":
                reply = "Silakan ketik kode menu dan jumlah tambahan yang ingin Kakak pesan (contoh: *2 x 3* atau *10 x 2*)."
                self.gateway.send_text(phone, reply)
                return reply

            # Coba parse pesanan dari input teks
            items, unknown = self.menu_manager.parse_order_input(text_clean)
            if items:
                self.order_manager.add_to_cart(phone, items)
                cart_summary = self.format_cart_summary(session["cart"])
                self.gateway.send_text(phone, cart_summary)
                return cart_summary
            else:
                reply = (
                    "Mohon maaf Kak, sistem belum mengenali kode menu tersebut. 😊\n"
                    "Silakan ketik kode sesuai daftar menu (contoh: *1 x 2* untuk 2 pcs Pempek Kapal Selam, atau *P1* untuk Paket 1).\n\n"
                    "Ketik *MENU* untuk melihat daftar kode menu lagi."
                )
                self.gateway.send_text(phone, reply)
                return reply

        # TAHAP 2: PEMILIHAN PENGIRIMAN (PICKUP VS DELIVERY)
        if state == "SELECTING_DELIVERY":
            if text_upper in ["1", "PICKUP", "AMBIL"]:
                session["delivery_type"] = "Ambil Sendiri di Warung (Pickup)"
                session["ongkir"] = 0
                session["state"] = "INPUT_NAME_ADDRESS"
                reply = (
                    "Pilihan yang pas! Kakak memilih *Ambil Sendiri di Warung (Pickup)* (Ongkir Rp 0).\n\n"
                    "Mohon ketik *NAMA KAKAK* dan *PERKIRAAN JAM PENGAMBILAN* ya Kak.\n"
                    "Contoh: *Budi, ambil jam 12.30 siang*"
                )
                self.gateway.send_text(phone, reply)
                return reply

            elif text_upper in ["2", "PAKET 1", "DELIVERY 1"]:
                opt = config.ONGKIR_OPTIONS["1"]
                session["delivery_type"] = f"Delivery {opt['nama']}"
                session["ongkir"] = opt["biaya"]
                session["state"] = "INPUT_NAME_ADDRESS"
                reply = (
                    f"Siap Kak! Kakak memilih *{opt['nama']}* (Ongkir Rp {opt['biaya']:,}).\n\n"
                    "Mohon ketik *NAMA KAKAK* dan *ALAMAT LENGKAP PENGANTARAN* (sertakan patokan bila ada) ya Kak.\n"
                    "Contoh: *Budi, Jl. Merdeka No. 12 dekat Masjid Al-Ikhlas*"
                )
                self.gateway.send_text(phone, reply)
                return reply

            elif text_upper in ["3", "PAKET 2", "DELIVERY 2"]:
                opt = config.ONGKIR_OPTIONS["2"]
                session["delivery_type"] = f"Delivery {opt['nama']}"
                session["ongkir"] = opt["biaya"]
                session["state"] = "INPUT_NAME_ADDRESS"
                reply = (
                    f"Siap Kak! Kakak memilih *{opt['nama']}* (Ongkir Rp {opt['biaya']:,}).\n\n"
                    "Mohon ketik *NAMA KAKAK* dan *ALAMAT LENGKAP PENGANTARAN* (sertakan patokan bila ada) ya Kak.\n"
                    "Contoh: *Budi, Kompleks Griya Indah Blok C3 No. 5*"
                )
                self.gateway.send_text(phone, reply)
                return reply

            else:
                reply = (
                    "Mohon pilih metode pengiriman dengan mengetik angka:\n"
                    "*1* untuk Ambil Sendiri (Pickup)\n"
                    "*2* untuk Delivery Paket 1 (Radius s.d. 3 KM)\n"
                    "*3* untuk Delivery Paket 2 (Radius 3 - 7 KM)"
                )
                self.gateway.send_text(phone, reply)
                return reply

        # TAHAP 3: PENGISIAN NAMA & ALAMAT / JAM AMBIL
        if state == "INPUT_NAME_ADDRESS":
            parts = [p.strip() for p in text_clean.split(",", 1)]
            nama = parts[0]
            alamat = parts[1] if len(parts) > 1 else text_clean

            session["nama_pembeli"] = nama
            session["alamat_pembeli"] = alamat

            # Buat pesanan resmi
            order_data = self.order_manager.create_pending_order(phone)
            order_id = order_data["order_id"]

            total_mkn_fmt = f"Rp {order_data['total_makanan']:,}".replace(",", ".")
            ongkir_fmt = f"Rp {order_data['ongkir']:,}".replace(",", ".")
            grand_fmt = f"Rp {order_data['grand_total']:,}".replace(",", ".")

            # 1. Pesan ke Pembeli
            cust_confirm = [
                f"Terima kasih banyak Kak *{nama}*! Pesanan Kakak telah kami catat: *{order_id}* 🎉",
                "",
                "📋 *RINGKASAN PESANAN KAKAK:*",
            ]
            for itm in order_data["items"]:
                cust_confirm.append(f"- {itm['qty']}x {itm['nama']} (Rp {itm['subtotal']:,})")
            cust_confirm.append(f"Subtotal Makanan: {total_mkn_fmt}")
            cust_confirm.append(f"Metode: {order_data['delivery_type']}")
            cust_confirm.append(f"Ongkir: {ongkir_fmt}")
            cust_confirm.append(f"*TOTAL KESELURUHAN: {grand_fmt}*")
            cust_confirm.append("")
            cust_confirm.append("⏳ *MOHON TUNGGU SEBENTAR YA KAK (1-3 Menit)...*")
            cust_confirm.append("Dapur kami sedang mengecek ketersediaan bahan dan antrean.")
            cust_confirm.append("Setelah dikonfirmasi siap oleh dapur, kami akan segera mengirimkan *Kode QRIS* untuk pembayaran. Terima kasih banyak atas kesabarannya! 🙏")

            cust_text = "\n".join(cust_confirm)
            self.gateway.send_text(phone, cust_text)

            # 2. Notifikasi ke WhatsApp Orang Tua (Admin Dapur)
            admin_notif = [
                "🔔 *ADA PESANAN BARU MASUK!*",
                f"*Kode Pesanan:* {order_id}",
                f"*Nama Pembeli:* {nama}",
                f"*Nomor WA:* {phone}",
                f"*Metode:* {order_data['delivery_type']}",
                f"*Alamat/Keterangan:* {alamat}",
                "",
                "🍲 *DETAIL MENU YANG DIPESAN:*",
            ]
            for itm in order_data["items"]:
                admin_notif.append(f"👉 *{itm['qty']}x {itm['nama']}* (Rp {itm['subtotal']:,})")
            admin_notif.append("")
            admin_notif.append(f"Total Makanan: {total_mkn_fmt}")
            admin_notif.append(f"Ongkir: {ongkir_fmt}")
            admin_notif.append(f"*TOTAL TAGIHAN: {grand_fmt}*")
            admin_notif.append("━━━━━━━━━━━━━━━━━━━━━━━━━")
            admin_notif.append("👉 *APAKAH BAHAN DAN DAPUR SIAP?*")
            admin_notif.append("Cukup balas chat ini:")
            admin_notif.append("Ketik *1* jika BAHAN READY (Kirim QRIS ke pembeli)")
            admin_notif.append("Ketik *2* jika BAHAN HABIS / DAPUR TUTUP")
            admin_notif.append("━━━━━━━━━━━━━━━━━━━━━━━━━")

            admin_text = "\n".join(admin_notif)
            self.gateway.send_text(self.admin_phone, admin_text)
            return cust_text

        # Tahap WAITING_KITCHEN
        if state == "WAITING_KITCHEN":
            reply = (
                f"Pesanan Kakak (*{session.get('current_order_id')}*) sedang dalam pengecekan dapur orang tua kami. "
                "Mohon bersabar sebentar ya Kak, kami akan segera mengabari begitu ada konfirmasi ketersediaan bahan. Terima kasih banyak! ⏳"
            )
            self.gateway.send_text(phone, reply)
            return reply

        # Fallback jika tidak sesuai kondisi apa pun
        fallback = "Halo Kak! Ada yang bisa kami bantu? Ketik *MENU* untuk melihat hidangan khas Palembang kami yang lezat dan gurih."
        self.gateway.send_text(phone, fallback)
        return fallback

    def format_cart_summary(self, cart):
        """Menghasilkan teks ringkasan keranjang belanja saat ini."""
        lines = ["🛒 *KERANJANG PESANAN KAKAK:*"]
        total = 0
        for item in cart:
            sub = item["subtotal"]
            total += sub
            lines.append(f"- {item['qty']}x {item['nama']} = Rp {sub:,}".replace(",", "."))

        lines.append(f"\n*Subtotal Makanan: Rp {total:,}*".replace(",", "."))
        lines.append("\n━━━━━━━━━━━━━━━━━━━")
        lines.append("Langkah selanjutnya:")
        lines.append("- Ketik *LANJUT* untuk memilih pengantaran & checkout.")
        lines.append("- Ketik *TAMBAH* atau langsung masukkan kode menu lain.")
        lines.append("- Ketik *BATAL* jika ingin mengulang keranjang.")
        return "\n".join(lines)

    def format_delivery_options(self):
        """Menghasilkan teks pilihan pengantaran dan paket ongkir."""
        p1 = config.ONGKIR_OPTIONS["1"]
        p2 = config.ONGKIR_OPTIONS["2"]
        lines = [
            "🛵 *PILIHAN PENGAMBILAN & PENGANTARAN:*",
            "Silakan pilih metode di bawah ini:",
            "",
            "👉 Ketik *1* : *Ambil Sendiri di Warung (Pickup)*",
            "   (Gratis ongkir / Rp 0)",
            "",
            f"👉 Ketik *2* : *{p1['nama']}*",
            f"   Ongkir: Rp {p1['biaya']:,} (Estimasi {p1['estimasi']})",
            "",
            f"👉 Ketik *3* : *{p2['nama']}*",
            f"   Ongkir: Rp {p2['biaya']:,} (Estimasi {p2['estimasi']})",
            "",
            "Silakan balas dengan mengetik angka *1*, *2*, atau *3*."
        ]
        return "\n".join(lines)
