import os
import re
import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    MessageHandler, filters
)
from dotenv import load_dotenv
from telegram.ext import MessageHandler, filters

ANTILINK_FILE = "antilink.json"
antilink_status = {}

def load_antilink_status():
    global antilink_status
    if os.path.exists(ANTILINK_FILE):
        try:
            with open(ANTILINK_FILE, "r") as f:
                data = json.load(f)
                # Konversi key ke int karena chat_id int
                antilink_status = {int(k): v for k, v in data.items()}
        except Exception as e:
            print("Gagal load antilink.json:", e)
            antilink_status = {}
    else:
        antilink_status = {}

def save_antilink_status():
    try:
        with open(ANTILINK_FILE, "w") as f:
            # Simpan key sebagai string agar JSON valid
            json.dump({str(k): v for k, v in antilink_status.items()}, f)
    except Exception as e:
        print("Gagal simpan antilink.json:", e)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_USERNAME = os.getenv("OWNER_USERNAME", "kingstoreganteng").lstrip("@")

group_access = {}

def check_owner(username: str):
    if not username:
        return False
    return username.lstrip("@") == OWNER_USERNAME

def parse_rekap_message(text):
    data_k = {}
    data_b = {}
    lines = text.strip().split('\n')

    section = None

    for line in lines:
        clean_line = line.strip()

        # Deteksi bagian K atau B (pakai unicode-aware dan titik dua fleksibel)
        if re.match(r'^[K𝐊𝗞𝑲𝔎𝕂𝓚𝙆]\s*[:：]?$', line, re.IGNORECASE):
            section = 'K'
            continue
        elif re.match(r'^[B𝐁𝗕𝑩𝔅𝕭𝓑𝙱]\s*[:：]?$', line, re.IGNORECASE):
            section = 'B'
            continue

        # Lewati baris kosong
        if clean_line == '':
            continue

        # Ambil nama dan jumlah
        match = re.match(r'(\S+)\s+(\d+)', clean_line)
        if match and section:
            name, amount = match.groups()
            amount = int(amount)
            if section == 'K':
                data_k[name] = amount
            elif section == 'B':
                data_b[name] = amount

    return data_k, data_b

import re

def parse_rekap_message(text):
    data_k = {}
    data_b = {}
    lines = text.strip().split('\n')

    section = None
    for line in lines:
        line = line.strip()

        # Deteksi section
        if re.match(r'^(K|KECIL)\s*[:：]?$', line, re.IGNORECASE):
            section = 'K'
            continue
        elif re.match(r'^(B|BESAR)\s*[:：]?$', line, re.IGNORECASE):
            section = 'B'
            continue

        if not section or not line:
            continue

        # Tangkap: nama jumlah [opsional tag]
        match = re.match(r'^(.+?)\s+(\d+)(?:\s+(\w+))?$', line)
        if match:
            name, amount, tag = match.groups()
            try:
                amount = int(amount)
            except:
                continue
            tag = tag.lower() if tag else ""
            if section == 'K':
                data_k[name.strip()] = (amount, tag)
            elif section == 'B':
                data_b[name.strip()] = (amount, tag)

    return data_k, data_b

def bold_unicode(text):
    normal = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    bold = "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇"
    return text.translate(str.maketrans(normal, bold))

def format_win_response(data_k, data_b, fee_percent, original_text):
    def after_fee(amount):
        doubled = amount * 2
        fee = int(doubled * fee_percent / 100)
        net = doubled - fee
        return net, fee

    def format_side(data):
        lines = []
        total_fee = 0
        for name, (amount, tag) in data.items():
            net, fee = after_fee(amount)
            total_fee += fee
            if tag.lower() == "lf":
                net_display = net - amount
            else:
                net_display = net
            tag_out = f" {tag.upper()}" if tag else ""
            lines.append(f"{name} {amount} // {net_display}{tag_out}")
        return lines, total_fee

    k_lines, fee_k = format_side(data_k)
    b_lines, fee_b = format_side(data_b)
    total_fee = fee_k + fee_b

    text_lower = original_text.lower()
    if "kecil" in text_lower and "besar" in text_lower:
        idx_k = text_lower.index("kecil")
        idx_b = text_lower.index("besar")
        first_label = bold_unicode("KECIL") if idx_k < idx_b else bold_unicode("BESAR")
        second_label = bold_unicode("BESAR") if idx_k < idx_b else bold_unicode("KECIL")
        first_lines = k_lines if idx_k < idx_b else b_lines
        second_lines = b_lines if idx_k < idx_b else k_lines
    elif "k" in text_lower and "b" in text_lower:
        idx_k = text_lower.index("k")
        idx_b = text_lower.index("b")
        first_label = bold_unicode("K") if idx_k < idx_b else bold_unicode("B")
        second_label = bold_unicode("B") if idx_k < idx_b else bold_unicode("K")
        first_lines = k_lines if idx_k < idx_b else b_lines
        second_lines = b_lines if idx_k < idx_b else k_lines
    else:
        # fallback
        first_label = bold_unicode("K")
        second_label = bold_unicode("B")
        first_lines = k_lines
        second_lines = b_lines

    response = (
        f"{first_label} : \n" + "\n".join(first_lines) + "\n\n" +
        f"{second_label} : \n" + "\n".join(second_lines) + "\n\n" +
        f"𝗙𝗘𝗘 𝗔𝗗𝗠𝗜𝗡 : {total_fee} 𝗞"
    )

    return response

import json
GROUP_ACCESS_FILE = "group_access.txt"

# Load data akses dari file
try:
    with open(GROUP_ACCESS_FILE, "r") as f:
        data = json.load(f)
        group_access = {
            int(k): datetime.datetime.fromisoformat(v) if v != "permanent" else None
            for k, v in data.items()
        }
except:
    group_access = {}

def save_group_access():
    with open(GROUP_ACCESS_FILE, "w") as f:
        json.dump({
            str(k): v.isoformat() if v is not None else "permanent"
            for k, v in group_access.items()
        }, f)

def is_group_access_allowed(chat_id):
    if chat_id not in group_access:
        return False
    access_time = group_access[chat_id]
    if access_time is None:  # artinya akses permanent, selalu diizinkan
        return True
    return access_time > datetime.datetime.now()

async def addakses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("Fitur ini hanya untuk group.")
        return

    user = update.effective_user
    if not check_owner(user.username):
        await update.message.reply_text("Kamu bukan owner bot!")
        return

    # Langsung aktifkan akses tanpa batas
    group_access[update.effective_chat.id] = None
    save_group_access()

    await update.message.reply_text(
        f"✅ Akses untuk group ini sekarang AKTIF."
    )



def bold_unicode(text):
    normal = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    bold = "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇"
    table = str.maketrans(normal, bold)
    return text.translate(table)

def format_rekap_response(data_k, data_b, original_text):
    total_k = sum(amount for amount, _ in data_k.values())
    total_b = sum(amount for amount, _ in data_b.values())
    total = total_k + total_b

    values_k = [str(amount) for amount, _ in data_k.values()]
    values_b = [str(amount) for amount, _ in data_b.values()]

    text_lower = original_text.lower()

    if "kecil" in text_lower and "besar" in text_lower:
        idx_k = text_lower.index("kecil")
        idx_b = text_lower.index("besar")
        first_label = "𝗞𝗘𝗖𝗜𝗟" if idx_k < idx_b else "𝗕𝗘𝗦𝗔𝗥"
        second_label = "𝗕𝗘𝗦𝗔𝗥" if idx_k < idx_b else "𝗞𝗘𝗖𝗜𝗟"
        first_total = total_k if idx_k < idx_b else total_b
        second_total = total_b if idx_k < idx_b else total_k
        first_list = values_k if idx_k < idx_b else values_b
        second_list = values_b if idx_k < idx_b else values_k
    elif "k" in text_lower and "b" in text_lower:
        idx_k = text_lower.index("k")
        idx_b = text_lower.index("b")
        first_label = "𝗞" if idx_k < idx_b else "𝗕"
        second_label = "𝗕" if idx_k < idx_b else "𝗞"
        first_total = total_k if idx_k < idx_b else total_b
        second_total = total_b if idx_k < idx_b else total_k
        first_list = values_k if idx_k < idx_b else values_b
        second_list = values_b if idx_k < idx_b else values_k
    else:
        first_label = "𝗞"
        second_label = "𝗕"
        first_total = total_k
        second_total = total_b
        first_list = values_k
        second_list = values_b

    response = (
        f"🔵 {first_label} : [{', '.join(first_list)}] = {first_total}\n\n"
        f"🔵 {second_label} : [{', '.join(second_list)}] = {second_total}"
    )

    if first_total < second_total:
        diff = second_total - first_total
        response += f"\n\n🐠{first_label} masih kekurangan {diff} untuk menyamai {second_label}."
    elif second_total < first_total:
        diff = first_total - second_total
        response += f"\n\n🐠{second_label} masih kekurangan {diff} untuk menyamai {first_label}."
    else:
        response += "\n\n⚖️ K dan B sudah seimbang"

    response += f"\n\n💰 Saldo Anda seharusnya: {total} 𝗞"

    return response, first_label, second_label, first_total, second_total

import asyncio

async def rekap_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("Fitur ini hanya bisa digunakan di group.")
        return

    if not is_group_access_allowed(update.effective_chat.id):
        await update.message.reply_text("Group ini belum punya akses. Gunakan /sewa untuk info.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Balas pesan berisi rekap K dan B, lalu ketik /rekap")
        return

    text = update.message.reply_to_message.text
    data_k, data_b = parse_rekap_message(text)
    
    if not data_k and not data_b:
        await update.message.reply_text("Format pesan salah. Minimal harus ada K atau B dengan nama + jumlah.")
        return

    # Format hasil
    response, first_label, second_label, first_total, second_total = format_rekap_response(data_k, data_b, text)
    followup = generate_roll_text(first_label, second_label, first_total, second_total)

    # Kirim pesan 1 — reply ke pesan /rekap
    await update.message.reply_text(response)

    # Delay sedikit biar urut rapi (opsional)
    await asyncio.sleep(1)

    # Kirim pesan 2 — tanpa reply
    await context.bot.send_message(chat_id=update.effective_chat.id, text=followup)

def generate_roll_text(first_label, second_label, first_total, second_total):
    if first_total < second_total:
        diff = second_total - first_total
        return f"{first_label} -{diff} 𝗔𝗟𝗟/𝗘𝗖𝗘𝗥 𝗦𝗨𝗡𝗚 𝗥𝗢𝗟𝗟"
    elif second_total < first_total:
        diff = first_total - second_total
        return f"{second_label} -{diff} 𝗔𝗟𝗟/𝗘𝗖𝗘𝗥 𝗦𝗨𝗡𝗚 𝗥𝗢𝗟𝗟"
    else:
        return "𝖢𝖤𝖪 𝖭𝖠𝖬𝖠 𝖬𝖠𝖲𝖨𝖭𝖦 𝖬𝖠𝖲𝖨𝖭𝖦, 𝖭𝖮 𝖣𝖱𝖠𝖬𝖠 𝖸𝖠𝖪 𝖮𝖳𝖶 𝖱𝖮𝖫𝖫"

async def win_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("Fitur ini hanya bisa digunakan di group.")
        return

    if not is_group_access_allowed(update.effective_chat.id):
        await update.message.reply_text("Group ini belum punya akses. Gunakan /sewa untuk info.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Balas pesan berisi rekap K dan B, lalu ketik /win <fee>")
        return

    if len(context.args) != 1:
        await update.message.reply_text("Gunakan: /win <fee_persen>")
        return

    try:
        fee_percent = float(context.args[0])
        if not (0 <= fee_percent <= 100):
            raise ValueError()
    except:
        await update.message.reply_text("Fee harus angka antara 0 dan 100.")
        return

    text = update.message.reply_to_message.text
    data_k, data_b = parse_rekap_message(text)
    if not data_k or not data_b:
        await update.message.reply_text("Format pesan salah.")
        return

    response = format_win_response(data_k, data_b, fee_percent, text)
    await update.message.reply_text(response)

async def handle_private_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("LU GADA AKSES BUAT MAKE BOT INI BG, PM DEV BOT DULU BIAR DI KASIH AKSES")

def is_antilink_on(chat_id):
    return antilink_status.get(chat_id, False)
    
async def antilink_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("Perintah ini hanya bisa digunakan di grup.")
        return

    if not context.args:
        await update.message.reply_text("Gunakan: /antilink on atau /antilink off")
        return

    status = context.args[0].lower()
    chat_id = update.effective_chat.id

    if status == "on":
        antilink_status[chat_id] = True
        save_antilink_status()
        await update.message.reply_text("✅ Antilink dan antiforward AKTIF.")
    elif status == "off":
        if chat_id in antilink_status:
            del antilink_status[chat_id]
            save_antilink_status()
        await update.message.reply_text("❌ Antilink dan antiforward NONAKTIF.")
    else:
        await update.message.reply_text("Gunakan: /antilink on atau /antilink off")
        
async def antilink_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat_id = update.effective_chat.id

    if not is_antilink_on(chat_id):
        return

    if not message:
        return

    # Jika pesan kosong (tidak ada teks dan caption), tidak perlu diproses
    if not message.text and not message.caption:
        return

    user = message.from_user
    mention = f"@{user.username}" if user.username else user.mention_html()

    # --- DETEKSI LINK ---
    # Cek semua entities di pesan (text, caption) untuk tipe url atau text_link
    entities = message.entities or message.caption_entities or []
    for entity in entities:
        if entity.type in ["url", "text_link"]:
            try:
                await message.delete()
                await context.bot.send_message(
                    chat_id,
                    f"⛔ {mention} Link tidak diizinkan di grup ini. Pesan sudah dihapus.",
                    parse_mode="HTML"
                )
            except Exception as e:
                print(f"Gagal hapus pesan link: {e}")
            return

    # --- DETEKSI PESAN FORWARD ---
    if (
        getattr(message, "forward_date", None) or
        getattr(message, "forward_from", None) or
        getattr(message, "forward_from_chat", None)
    ):
        try:
            await message.delete()
            await context.bot.send_message(
                chat_id,
                f"⛔ {mention} Pesan terusan (forward) tidak diizinkan di grup ini.",
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Gagal hapus pesan forward: {e}")
        return

    # --- DETEKSI PESAN CERITA (TOPIC MESSAGE) ---
    # Jika grup menggunakan fitur topik (discussion threads)
    if getattr(message, 'is_topic_message', False):
        try:
            await message.delete()
            await context.bot.send_message(
                chat_id,
                f"⛔ {mention} Cerita / topik tidak diizinkan di grup ini.",
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Gagal hapus pesan cerita: {e}")
        return

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Perintah tidak dikenali.")
    
def main():
    print(f"BOT_TOKEN: {BOT_TOKEN}")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("addakses", addakses))
    app.add_handler(CommandHandler("rekap", rekap_command))
    app.add_handler(CommandHandler("win", win_command))
    app.add_handler(CommandHandler("antilink", antilink_command))
    
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE, handle_private_chat))
    app.add_handler(MessageHandler(filters.COMMAND, unknown))
    app.add_handler(MessageHandler(filters.ALL & filters.ChatType.GROUPS, antilink_filter))
    

    print("Bot sudah jalan...")
    app.run_polling()

if __name__ == "__main__":
    main()