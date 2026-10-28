import requests
import json
import logging
import os
import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("WhatsAppGateway")

class WhatsAppGateway:
    def __init__(self, provider=None, token=None):
        self.provider = provider or config.GATEWAY_PROVIDER
        self.token = token or config.FONNTE_TOKEN
        self.api_url = "https://api.fonnte.com/send"

    def clean_phone_number(self, phone):
        """Memformat nomor telepon menjadi standar internasional tanpa karakter aneh."""
        phone = str(phone).strip()
        # Hilangkan simbol seperti +, -, spasi, tanda kurung
        for ch in ["+", "-", " ", "(", ")", "@s.whatsapp.net", "@c.us"]:
            phone = phone.replace(ch, "")

        # Ubah awalan 08 menjadi 628
        if phone.startswith("08"):
            phone = "628" + phone[2:]
        elif phone.startswith("8"):
            phone = "62" + phone

        return phone

    def send_text(self, target, message):
        """Mengirim pesan teks ke nomor WhatsApp tujuan."""
        target_clean = self.clean_phone_number(target)

        # Mode Uji Coba (Mock / Tanpa Pulsa Gateway)
        if self.provider == "mock" or not self.token or self.token == "ISI_DENGAN_TOKEN_FONNTE_ANDA":
            logger.info(f"[MOCK WA] Kirim Teks ke {target_clean}:\n{message}\n" + "="*40)
            return {"status": True, "detail": "Mock message logged"}

        # Mode Fonnte WhatsApp Gateway
        headers = {
            "Authorization": self.token
        }
        payload = {
            "target": target_clean,
            "message": message,
            "countryCode": "62"
        }

        try:
            response = requests.post(self.api_url, data=payload, headers=headers, timeout=15)
            res_data = response.json()
            logger.info(f"Fonnte send_text response: {res_data}")
            return res_data
        except Exception as e:
            logger.error(f"Gagal mengirim pesan WA ke {target_clean}: {e}")
            return {"status": False, "error": str(e)}

    def send_image(self, target, image_url, caption=""):
        """Mengirim file gambar (QRIS) dengan caption ke WhatsApp tujuan."""
        target_clean = self.clean_phone_number(target)

        if self.provider == "mock" or not self.token or self.token == "ISI_DENGAN_TOKEN_FONNTE_ANDA":
            logger.info(f"[MOCK WA GAMBAR] Kirim Gambar ke {target_clean}:\nURL: {image_url}\nCaption: {caption}\n" + "="*40)
            return {"status": True, "detail": "Mock image message logged"}

        headers = {
            "Authorization": self.token
        }
        payload = {
            "target": target_clean,
            "url": image_url,
            "caption": caption,
            "countryCode": "62"
        }

        try:
            response = requests.post(self.api_url, data=payload, headers=headers, timeout=20)
            res_data = response.json()
            logger.info(f"Fonnte send_image response: {res_data}")
            return res_data
        except Exception as e:
            logger.error(f"Gagal mengirim gambar WA ke {target_clean}: {e}")
            return {"status": False, "error": str(e)}
