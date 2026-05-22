from enum import Enum, auto
from nlp_engine import NLPEngine

class State(Enum):
    IDLE = auto()
    ORDERING = auto()
    CONFIRMATION = auto()
    PAYMENT = auto()
    
class CoffeeFSM:
    def __init__(self):
        self.state = State.IDLE
        self.nlp = NLPEngine()
        self.cart = [] 
        self.response = ""

    def get_response(self):
        return self.response

    def calculate_total(self):
        return sum(item['price'] * item['qty'] for item in self.cart)
    
    def get_menu_text(self):
        """Fungsi bantuan untuk merangkai teks daftar menu"""
        teks_menu = "**📜 Daftar Menu Logic Coffee:**\n\n"
        for key, data in self.nlp.menu_data.items():
            teks_menu += f"- {data['emoji']} **{key.capitalize()}** (Rp {data['price']:,}): *{data['desc']}*\n"
        teks_menu += "\nSilakan ketik pesanan Anda (contoh: *'Pesan 2 teh, 1 espresso'*)."
        return teks_menu

    def reduce_cart(self, item_to_reduce, qty_to_remove):
        """Logika untuk mengurangi qty item atau menghapusnya jika qty <= 0"""
        found = False
        message = ""
        
        # Cari item di cart
        for item in self.cart:
            if item['item'] == item_to_reduce:
                item['qty'] -= qty_to_remove
                found = True
                if item['qty'] <= 0:
                    self.cart.remove(item)
                    message = f"❌ **{item_to_reduce}** telah dihapus dari keranjang."
                else:
                    message = f"📉 **{item_to_reduce}** dikurangi {qty_to_remove}. Sisa: {item['qty']}."
                break
        
        if not found:
            message = f"Gagal: **{item_to_reduce}** tidak ditemukan di keranjang Anda."
        return message

    def step(self, user_input=""):
        user_input = user_input.strip()
        intent = self.nlp.detect_intent(user_input)

        # 1. GLOBAL RESET SYSTEM
        if intent == "RESET_SYSTEM":
            self.__init__()
            self.response = "Sistem di-reset total. Halo! Mau pesan apa?"
            return

        # --- STATE LOGIC: ORDERING ---
        if self.state == State.IDLE:
            self.state = State.ORDERING
            self.response = "Halo! Mau pesan apa hari ini? Ketik 'menu' untuk melihat pilihan."

        elif self.state == State.ORDERING:
            if intent == "ASK_MENU":
                self.response = self.get_menu_text()
            
            # FITUR BARU: Batalkan Semua
            elif intent == "CANCEL_ALL":
                self.cart = []
                self.response = "Keranjang telah dikosongkan. Mau pesan yang lain?"

            # FITUR BARU: Kurangi/Batalkan Item Tertentu
            elif intent == "REDUCE_ITEM":
                items_to_remove = self.nlp.parse_orders(user_input)
                if items_to_remove:
                    results = []
                    for itm in items_to_remove:
                        res = self.reduce_cart(itm['item'], itm['qty'])
                        results.append(res)
                    self.response = "\n".join(results)
                else:
                    self.response = "Item apa yang ingin dibatalkan? Contoh: *'batalkan 1 kopi'*."

            elif intent == "CHECKOUT":
                if not self.cart:
                    self.response = "Keranjang masih kosong."
                else:
                    self.state = State.CONFIRMATION
                    self.response = f"Total: **Rp {self.calculate_total():,}**. Lanjut bayar? (Ya/Tidak)"

            else:
                # Logika Penambahan Pesanan (Default)
                new_orders = self.nlp.parse_orders(user_input)
                if new_orders:
                    for order in new_orders:
                        # Cek jika item sudah ada, tambah qty saja
                        existing = next((i for i in self.cart if i['item'] == order['item']), None)
                        if existing:
                            existing['qty'] += order['qty']
                        else:
                            # Ambil info harga & emoji dari menu_data
                            menu_info = self.nlp.menu_data[order['item']]
                            order.update({"price": menu_info['price'], "emoji": menu_info['emoji']})
                            self.cart.append(order)
                    self.response = "✅ Pesanan ditambahkan. Ada lagi? (Ketik 'bayar' untuk selesai)"
                else:
                    self.response = "Maaf, saya tidak mengerti. Coba: *'pesan 2 kopi'* atau *'hapus 1 kopi'*."

        elif self.state == State.CONFIRMATION:
            intent = self.nlp.detect_intent(user_input)
            if intent == "YES":
                self.state = State.PAYMENT
                self.step() # Auto-step
            elif intent == "NO":
                self.state = State.ORDERING
                self.response = "Oke, silakan tambah pesanan lagi."
            else:
                self.response = "Jawab 'Ya' atau 'Tidak'."

        elif self.state == State.PAYMENT:
            total = self.calculate_total()
            self.response = f"🎉 Terima kasih! Pembayaran Rp {total:,} diterima. Pesanan diproses."
            self.state = State.IDLE