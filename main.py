import telebot
import json
import os
import re
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telegram_bot_calendar import DetailedTelegramCalendar
from datetime import datetime


# Thay bằng token bot của bạn
TOKEN = "7712345222:AAEraUt4msKec3Zjrs2TmPIDHbHXg0ll0KU"
bot = telebot.TeleBot(TOKEN)

# ID Admin
ADMIN_ID = 7514889321

# File lưu danh sách User
USER_FILE = "allowed_users.json"

# Kiểm tra và tạo file JSON nếu chưa tồn tại
if not os.path.exists(USER_FILE):
    with open(USER_FILE, "w") as f:
        json.dump([], f)

# Tải danh sách User từ file
def load_users():
    if os.path.exists(USER_FILE):
        try:
            with open(USER_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, dict):  
                    return data
        except json.JSONDecodeError:
            print("⚠ Lỗi JSON! Đang tạo file mới...")
    return {}  

# Danh sách User ID được phép sử dụng bot
ALLOWED_USERS = load_users()  

# Lưu danh sách User vào file
def save_users():
    with open(USER_FILE, "w") as f:
        json.dump(ALLOWED_USERS, f, indent=4)  

# Kiểm tra quyền truy cập
def is_user_allowed(user_id):
    return user_id in ALLOWED_USERS or user_id == ADMIN_ID

@bot.message_handler(commands=['start'])
def start_command(message):
    bot.reply_to(message, "👋 Chào mừng bạn! Gửi một chuỗi MD5 để tôi phân tích giúp bạn.")

@bot.message_handler(commands=['id'])
def get_user_id(message):
    user_id = message.from_user.id
    bot.reply_to(message, f"🆔 **User ID của bạn:** `{user_id}`", parse_mode="Markdown")

@bot.message_handler(commands=['help'])
def show_help(message):
    help_text = "📌 **DANH SÁCH LỆNH BOT** 📌\n\n" \
                "🔹 /start - Bắt đầu bot\n" \
                "🔹 /help - Hiển thị danh sách lệnh\n" \
                "🔹 /id - Lấy User ID\n"
    if message.from_user.id == ADMIN_ID:
        help_text += ("\n👑 **LỆNH DÀNH CHO QUẢN TRỊ VIÊN** 👑\n"
                      "✅ /adduser <id> - Thêm người dùng có thời gian\n"
                      "💫 /themuser <id> - Thêm người dùng không thời gian\n"
                      "❌ /removeuser <id> - Xóa người dùng\n"
                      "📋 /listusers - Hiển thị danh sách người dùng\n"
                      "📢 /broadcast <nội dung> - Gửi thông báo\n")
    bot.reply_to(message, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['themuser'])
def add_user(message):
    if message.from_user.id != ADMIN_ID:
        return bot.reply_to(message, "🚫 Bạn không có quyền!")
    try:
        new_user_id = message.text.split()[1]
        if not new_user_id.isdigit():
            raise ValueError("ID không hợp lệ!")
        if new_user_id in ALLOWED_USERS:
            return bot.reply_to(message, f"⚠ User `{new_user_id}` đã tồn tại!", parse_mode="Markdown")
        ALLOWED_USERS[new_user_id] = "forever"  # Hoặc None nếu bạn muốn
        save_users()
        bot.reply_to(message, f"✅ Đã thêm `{new_user_id}` vào danh sách!", parse_mode="Markdown")
    except:
        bot.reply_to(message, "⚠ Vui lòng nhập ID hợp lệ!")
# Dictionary lưu trạng thái thêm user
adding_users = {}

# Hàm dịch lịch sang tiếng Việt
def vietnamese_calendar(calendar_markup):
    if not isinstance(calendar_markup, InlineKeyboardMarkup):
        return calendar_markup
    
    month_translations = {
        "Jan": "Tháng 1", "Feb": "Tháng 2", "Mar": "Tháng 3", "Apr": "Tháng 4",
        "May": "Tháng 5", "Jun": "Tháng 6", "Jul": "Tháng 7", "Aug": "Tháng 8",
        "Sep": "Tháng 9", "Oct": "Tháng 10", "Nov": "Tháng 11", "Dec": "Tháng 12"
    }
    
    for row in calendar_markup.keyboard:
        for button in row:
            if any(month in button.text for month in month_translations.keys()):
                for en, vi in month_translations.items():
                    button.text = button.text.replace(en, vi)
            elif button.text == "<<":
                button.text = "⏪ Trước"
            elif button.text == ">>":
                button.text = "Tiếp ⏩"
            elif button.text == "OK":
                button.text = "✅ Xác nhận"
    return calendar_markup

@bot.message_handler(commands=['adduser'])
def add_user_command(message):
    if message.from_user.id != ADMIN_ID:
        return bot.reply_to(message, "🚫 Bạn không có quyền!")
    msg = bot.reply_to(message, "🆔 Nhập User ID:")
    bot.register_next_step_handler(msg, process_user_id)

def process_user_id(message):
    if not message.text.isdigit():
        return bot.reply_to(message, "⚠ Vui lòng nhập số hợp lệ!")
    user_id = message.text
    adding_users[message.from_user.id] = {'user_id': user_id}
    calendar, step = DetailedTelegramCalendar(locale='en').build()
    calendar = vietnamese_calendar(calendar)
    bot.send_message(message.chat.id, "📅 Chọn ngày hết hạn:", reply_markup=calendar)

@bot.callback_query_handler(func=DetailedTelegramCalendar.func())
def process_calendar(callback_query):
    result, key, step = DetailedTelegramCalendar(locale='en').process(callback_query.data)
    if not result and key:
        key = vietnamese_calendar(key)
        bot.edit_message_text("📅 Chọn ngày:", callback_query.message.chat.id,
                              callback_query.message.message_id, reply_markup=key)
    elif result:
        adding_users[callback_query.from_user.id]['expiry_date'] = result
        msg = bot.send_message(callback_query.message.chat.id, "⏰ Nhập giờ hết hạn (HH:MM):")
        bot.register_next_step_handler(msg, process_time)

def process_time(message):
    try:
        expiry_time = datetime.strptime(message.text, "%H:%M")
        user_id = adding_users[message.from_user.id]['user_id']
        expiry_date = adding_users[message.from_user.id]['expiry_date']
        expiry_datetime = datetime.combine(expiry_date, expiry_time.time())
        ALLOWED_USERS[str(user_id)] = expiry_datetime.strftime("%Y-%m-%d %H:%M:%S")
        save_users()
        bot.reply_to(message, f"✅ Đã thêm User `{user_id}` đến `{expiry_datetime}`", parse_mode="Markdown")
    except ValueError:
        bot.reply_to(message, "⚠ Định dạng không hợp lệ! Hãy nhập đúng HH:MM.")
@bot.message_handler(commands=['removeuser'])
def remove_user(message):
    if message.from_user.id != ADMIN_ID:
        return bot.reply_to(message, "🚫 Bạn không có quyền!")
    try:
        remove_user_id = message.text.split()[1]
        if remove_user_id in ALLOWED_USERS:
            del ALLOWED_USERS[remove_user_id]
            save_users()
            bot.reply_to(message, f"❌ Đã xóa `{remove_user_id}`", parse_mode="Markdown")
        else:
            bot.reply_to(message, "⚠ ID không tồn tại!")
    except IndexError:
        bot.reply_to(message, "⚠ Vui lòng nhập ID hợp lệ!")

@bot.message_handler(commands=['broadcast'])
def broadcast_message(message):
    if message.from_user.id != ADMIN_ID:
        return bot.reply_to(message, "🚫 Bạn không có quyền!")

    msg = bot.reply_to(message, "📢 Hãy gửi nội dung thông báo (văn bản, ảnh, GIF, sticker, emoji, v.v.):")
    bot.register_next_step_handler(msg, process_broadcast)

def process_broadcast(message):
    failed_users = []
    
    for user_id in ALLOWED_USERS:
        try:
            if message.text:
                bot.send_message(user_id, f"📢 **THÔNG BÁO:**\n\n{message.text}", parse_mode="Markdown")
            elif message.photo:
                bot.send_photo(user_id, message.photo[-1].file_id, caption="📢 **THÔNG BÁO**")
            elif message.video:
                bot.send_video(user_id, message.video.file_id, caption="📢 **THÔNG BÁO**")
            elif message.animation:  # GIF
                bot.send_animation(user_id, message.animation.file_id, caption="📢 **THÔNG BÁO**")
            elif message.sticker:
                bot.send_sticker(user_id, message.sticker.file_id)
            elif message.document:
                bot.send_document(user_id, message.document.file_id, caption="📢 **THÔNG BÁO**")
            else:
                bot.send_message(user_id, "📢 **THÔNG BÁO:** (Nội dung không xác định)")

        except Exception:
            failed_users.append(user_id)

    if failed_users:
        bot.reply_to(message, f"⚠ Không thể gửi đến một số người dùng: {', '.join(map(str, failed_users))}")
    else:
        bot.reply_to(message, "✅ Đã gửi thông báo đến tất cả người dùng!")

@bot.message_handler(commands=['listusers'])
def list_users(message):
    if message.from_user.id != ADMIN_ID:
        return bot.reply_to(message, "🚫 Bạn không có quyền!")

    try:
        if not ALLOWED_USERS:
            return bot.reply_to(message, "📋 Danh sách trống!")

        user_list = []
        for user_id in ALLOWED_USERS:
            try:
                user_info = bot.get_chat(user_id)
                username = user_info.username if user_info.username else user_info.first_name
                
               
                username = re.sub(r"([_*\[\]()~`>#+\-=|{}.!])", r"\\\1", username)
                user_list.append(f"🔹 `{username}` \\(ID: `{user_id}`\\)")
            except Exception:
                user_list.append(f"🔹 ID: `{user_id}` \\(Không thể lấy tên\\)")

        user_list_text = "\n".join(user_list)
        bot.reply_to(message, f"📋 *Danh sách người dùng:*\n{user_list_text}", parse_mode="MarkdownV2")

    except Exception as e:
        bot.reply_to(message, f"⚠ Lỗi khi lấy danh sách: `{e}`", parse_mode="MarkdownV2")


@bot.message_handler(func=lambda message: len(message.text) == 32 and all(c in "0123456789abcdefABCDEF" for c in message.text))
def analyze_md5(message):
    try:
        md5_int = int(message.text, 16)
        last_two_digits = md5_int % 100

        if last_two_digits >= 50:
            result = "🔥 **TÀI**"
            probability_tai = 70 + (last_two_digits - 50) // 5  # Xác suất TÀI từ 70% - 90%
            probability_xiu = 100 - probability_tai
        else:
            result = "❄️ **XỈU**"
            probability_xiu = 70 + (50 - last_two_digits) // 5  # Xác suất XỈU từ 70% - 90%
            probability_tai = 100 - probability_xiu

        response = (f"🎰 **KẾT QUẢ PHÂN TÍCH MD5** 🎰\n\n"
                    f"🔍 **MD5 Hash:** `{message.text}`\n"
                    f"🎲 **Số cuối MD5:** `{last_two_digits}`\n"
                    f"⚖ **Kết quả:** {result}\n"
                    f"💥 **Xác suất TÀI:** `{probability_tai}%`\n"
                    f"💦 **Xác suất XỈU:** `{probability_xiu}%`\n\n"
                    f"👑 **Admin:** [Sew2k](https://t.me/tedexe)\n"
                    f"🛠 **Developer:** [Sew2k](https://t.me/tedexe)")

        bot.reply_to(message, response, parse_mode="Markdown", disable_web_page_preview=True)
    except:
        bot.reply_to(message, "❌ Lỗi! Vui lòng gửi chuỗi MD5 hợp lệ.")


print("🔄 Bot đang chạy...")
bot.polling(none_stop=True)
