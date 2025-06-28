# main.py
import json
import os
import time
from aiogram.types import ChatJoinRequest
from datetime import datetime
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.filters import StateFilter
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from urllib.parse import quote
from aiogram.exceptions import TelegramBadRequest
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode, ChatMemberStatus
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.markdown import hlink

import asyncio

API_TOKEN = "7941332671:AAFqVeJSbVrGZh7YLpPyIHF4IybGv4LPxSY"
SUPER_ADMIN_ID = 7126044134
DATA_FILE = "data.json"
JOIN_REQ_FILE = "join_requests.json"

# Bot va Dispatcher
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Fayldan ma'lumotlarni yuklash yoki yangi yaratish
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
else:
    data = {
        "admins": [SUPER_ADMIN_ID],
        "movies": {},
        "channels": [],
        "bots": [],
        "force_sub": True,
        "users": {}
    }
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

ADMINS = data["admins"]
MOVIES = data["movies"]
channels = data["channels"]
bots = data["bots"]
force_sub = data.get("force_sub", True)
USERS = data.get("users", {})

# --- Foydalanuvchilarni va ma’lumotlarni saqlash ---
def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "admins": ADMINS,
            "movies": MOVIES,
            "channels": channels,
            "bots": bots,
            "force_sub": force_sub,
            "users": USERS
        }, f, ensure_ascii=False, indent=4)

def update_user(user_id: int):
    USERS[str(user_id)] = int(time.time())
    save_data()


def count_users():
    total = len(USERS)
    now = int(time.time())
    active = sum(1 for t in USERS.values() if now - t < 3 * 24 * 3600)
    return total, active

def count_new_24h():
    return sum(1 for t in USERS.values() if int(time.time()) - t < 24 * 3600)

def count_new_7d():
    return sum(1 for t in USERS.values() if int(time.time()) - t < 7 * 24 * 3600)

def count_new_30d():
    return sum(1 for t in USERS.values() if int(time.time()) - t < 30 * 24 * 3600)

def total_movies_count():
    return len(MOVIES)



# FSM States
class AddMovie(StatesGroup):
    waiting_for_code = State()         # Kino kodi
    waiting_for_video = State()        # Kino fayli
    waiting_for_description = State()  # Kino haqida matnli tavsif
    
class AdminManage(StatesGroup):
    add = State()
    remove = State()

class AdminRemove(StatesGroup):
    id = State()

class DeleteMovie(StatesGroup):
    waiting_for_code = State()

class AdBroadcast(StatesGroup):
    waiting_for_content = State()
    waiting_for_text_with_link = State()

class SubSettings(StatesGroup):
    public_channel_add = State()
    private_channel_add = State()
    channel_remove = State()  # bu bizga kerak
    bot_add = State()
    private_channel_manual_url = State()
    bot_remove = State()

# Router
router = Router()

@router.chat_join_request()
async def handle_join_request(event: ChatJoinRequest, bot: Bot):
    user_id = str(event.from_user.id)
    channel_id = str(event.chat.id)

    file_path = "join_requests.json"
    if not os.path.exists(file_path):
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump({}, f)

    with open(file_path, "r+", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = {}

        if channel_id not in data:
            data[channel_id] = []

        if user_id not in data[channel_id]:
            data[channel_id].append(user_id)

        f.seek(0)
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.truncate()

def add_join_request_to_json(user_id: int, channel_id: int):
    file_path = "join_requests.json"
    user_id_str = str(user_id)
    channel_id_str = str(channel_id)  # 🔁 ID string formatda saqlanadi

    if not os.path.exists(file_path):
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump({}, f)

    with open(file_path, "r+", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = {}

        if channel_id_str not in data:
            data[channel_id_str] = []

        if user_id_str not in data[channel_id_str]:
            data[channel_id_str].append(user_id_str)
            print(f"[JOIN] {user_id} qo‘shildi: {channel_id_str}")

        f.seek(0)
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.truncate()

def is_user_in_join_requests(user_id: int, channel_id: int) -> bool:
    file_path = "join_requests.json"
    user_id_str = str(user_id)
    channel_id_str = str(channel_id)  # kanal ID ham string ko‘rinishda saqlanadi

    if not os.path.exists(file_path):
        return False

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        return False

    return user_id_str in data.get(channel_id_str, [])

def fix_channels_format():
    DATA_FILE = "data.json"

    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({"channels": [], "join_requests": {}}, f, ensure_ascii=False, indent=2)

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = {"channels": [], "join_requests": {}}

    fixed_channels = []
    for ch in data.get("channels", []):
        if isinstance(ch, str):
            # Agar faqat URL bo'lsa (eski format) — type aniqlaymiz, id yo'q
            ch_type = "private" if "+" in ch or "joinchat" in ch else "public"
            fixed_channels.append({
                "url": ch.rstrip("/"),
                "type": ch_type,
                "id": None  # id keyin aniqlanadi
            })
        elif isinstance(ch, dict):
            ch["url"] = ch.get("url", "").rstrip("/")  # URL normalize
            if "id" not in ch:
                ch["id"] = None  # agar yo‘q bo‘lsa qo‘shamiz
            fixed_channels.append(ch)

    data["channels"] = fixed_channels

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return fixed_channels

# Global o‘zgaruvchi
channels = fix_channels_format()

def init_join_request_channel_in_data(channel_id: int, ch_type: str):
    if ch_type != "private":
        return  # faqat private kanal uchun ishlaydi

    channel_id = str(channel_id)  # ID string ko‘rinishda saqlanadi

    file_path = "data.json"

    if not os.path.exists(file_path):
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump({"join_requests": {}}, f, indent=2, ensure_ascii=False)

    with open(file_path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = {"join_requests": {}}

    if "join_requests" not in data:
        data["join_requests"] = {}

    if channel_id not in data["join_requests"]:
        data["join_requests"][channel_id] = []

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)



def add_join_request_to_data(user_id: int, channel_id: int):
    channel_id = str(channel_id)
    user_id = str(user_id)

    file_path = "data.json"

    if not os.path.exists(file_path):
        data = {"join_requests": {}}
    else:
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = {"join_requests": {}}

    if "join_requests" not in data:
        data["join_requests"] = {}

    if channel_id not in data["join_requests"]:
        data["join_requests"][channel_id] = []

    if user_id not in data["join_requests"][channel_id]:
        data["join_requests"][channel_id].append(user_id)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def has_user_requested_join(user_id: int, channel_id: int) -> bool:
    file_path = "join_requests.json"
    channel_id = str(channel_id)  # kanal ID stringga o‘tkaziladi

    if not os.path.exists(file_path):
        return False

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        return False

    return str(user_id) in data.get(channel_id, [])


def remove_channel_from_join_requests_data(channel_id: int):
    channel_id_str = str(channel_id)

    if not os.path.exists("data.json"):
        return

    with open("data.json", "r+", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = {}

        if "join_requests" in data and channel_id_str in data["join_requests"]:
            del data["join_requests"][channel_id_str]

            f.seek(0)
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.truncate()

def create_channel_entry_in_join_requests(channel_id: int):
    """
    Private kanal uchun join_requests.json faylida kanal ID asosida bo‘sh ro'yxat yaratadi.
    """
    file_path = "join_requests.json"
    channel_id_str = str(channel_id)

    if not os.path.exists(file_path):
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump({}, f)

    with open(file_path, "r+", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = {}

        if channel_id_str not in data:
            data[channel_id_str] = []

        f.seek(0)
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.truncate()


# --- Join request eventni ushlab olish ---
def add_join_request(user_id: int, channel_id: int):
    """
    Foydalanuvchi join request yuborganda, kanal ID asosida uni ro'yxatga qo‘shadi.
    """
    channel_id_str = str(channel_id)
    user_id_str = str(user_id)

    if not os.path.exists("data.json"):
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump({}, f)

    with open("data.json", "r+", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = {}

        if "join_requests" not in data:
            data["join_requests"] = {}

        if channel_id_str not in data["join_requests"]:
            data["join_requests"][channel_id_str] = []

        if user_id_str not in data["join_requests"][channel_id_str]:
            data["join_requests"][channel_id_str].append(user_id_str)
            print(f"[JOIN] {user_id} qo‘shildi: {channel_id}")

        f.seek(0)
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.truncate()
    
# --- Callback: Tekshirish tugmasi bosilganda ---
@router.callback_query(F.data == "check_sub")
async def check_subscription(call: CallbackQuery, bot: Bot):
    user_id = call.from_user.id
    not_joined = []

    for ch in channels:
        ch_type = ch.get("type", "public")
        ch_id = str(ch.get("id"))  # kanal ID string ko‘rinishda

        if ch_type == "private":
            if not is_user_in_join_requests(user_id, ch_id):
                not_joined.append(ch)
        else:
            try:
                username = ch["url"].replace("https://t.me/", "").strip("/")
                member = await bot.get_chat_member(chat_id=f"@{username}", user_id=user_id)
                if member.status in ["left", "kicked"]:
                    not_joined.append(ch)
            except Exception:
                not_joined.append(ch)

    if not not_joined:
        text = f"✅ A'zolik tasdiqlandi! Endi kino kodini yuborishingiz mumkin.\n👤 @{call.from_user.username or call.from_user.first_name}"
        if call.message.text != text:
            try:
                await call.message.edit_text(text)
            except TelegramBadRequest as e:
                if "message is not modified" not in str(e):
                    raise
        else:
            await call.answer("🔁 Siz allaqachon a’zo deb hisoblangansiz.", show_alert=True)
    else:
        markup, _ = await get_subscription_markup_dynamic(user_id, bot)
        await call.answer("☝️ Ba'zi kanallarga hali a’zo bo‘lmagansiz!", show_alert=True)
        await call.message.edit_reply_markup(reply_markup=markup)
            
async def get_subscription_markup_dynamic(user_id: int, bot: Bot):
    not_joined = await check_membership(user_id, bot)
    markup = InlineKeyboardBuilder()

    for ch in not_joined:
        if ch["type"] == "public":
            markup.row(
                InlineKeyboardButton(text="📢 A'zo bo'lish", url=ch["url"])
            )
        else:
            # Private kanal bo‘lsa – faqat URL tugmasi (subscribe bo‘lishi uchun)
            markup.row(
                InlineKeyboardButton(text="🔐 Kanal", url=ch["url"])
            )

    markup.row(InlineKeyboardButton(text="🔄 Tekshirish", callback_data="check_sub"))
    return markup.as_markup(), not_joined

    # Tugmalarni yasaymiz
    for ch in not_joined:
        markup.row(InlineKeyboardButton(text="📢 A'zo bo'lish", url=ch["url"]))

    markup.row(InlineKeyboardButton(text="🔄 Tekshirish", callback_data="check_sub"))

    return markup.as_markup(), not_joined


async def check_membership(user_id: int, bot: Bot):
    if user_id in ADMINS:  # 🛑 Agar admin bo‘lsa, hech narsa tekshirmasdan ruxsat ber
        return []

    unsubscribed = []

    for ch in channels:
        ch_type = ch.get("type", "public")
        ch_id = str(ch.get("id"))

        if ch_type == "public":
            try:
                member = await bot.get_chat_member(chat_id=ch_id, user_id=user_id)
                if member.status in ["left", "kicked"]:
                    unsubscribed.append(ch)
            except Exception:
                unsubscribed.append(ch)

        elif ch_type == "private":
            if not has_user_requested_join(user_id, ch_id):
                unsubscribed.append(ch)

    return unsubscribed

@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    update_user(user_id)

    if user_id in ADMINS:
        await message.answer("🛠 Admin panelga xush kelibsiz!", reply_markup=get_admin_panel())
        return

    await bot.send_photo(
        chat_id=message.chat.id,
        photo="https://s8.ezgif.com/tmp/ezgif-88a50b3eeccb89.png",
        caption=f"👋 Assalomu alaykum, {message.from_user.first_name}!\n\n✍️ Iltimos, kino kodini yuboring.",
    )

    if force_sub:
        await asyncio.sleep(0.2)
        markup, not_joined_channels = await get_subscription_markup_dynamic(user_id, bot)
        if not_joined_channels:
            await message.answer("🎬 Kino olish uchun quyidagi kanallarga a'zo bo‘ling!", reply_markup=markup)
            return  # ❗ Obuna bo'lmaguncha kino kodini yozishga ruxsat yo‘q 

@router.message(StateFilter(None), F.text.regexp(r"^\d{3,4}$"))
async def handle_movie_code(message: Message):
    user_id = message.from_user.id
    code = message.text.strip()

    # ✅ Majburiy obuna tekshiruvi
    if force_sub:
        unsubscribed = await check_membership(user_id, bot)
        if unsubscribed:
            markup, _ = await get_subscription_markup_dynamic(user_id, bot)
            await message.answer("❗ Avval kanallarga a’zo bo‘ling!", reply_markup=markup)
            return

    # ✅ Foydalanuvchi xabari o‘chiriladi
    try:
        await message.delete()
    except:
        pass

    # ✅ Kino kodi mavjud bo‘lsa
    if code in MOVIES:
        movie = MOVIES[code]

        # ✅ Faqat oddiy foydalanuvchi bo‘lsa — ko‘rishlar sonini oshiramiz
        if user_id not in ADMINS:
            movie.setdefault("views", 0)
            movie["views"] += 1
            save_data()

        # ✅ Kino tavsifi va admin statistikasi
        caption = movie.get("description", "")
        if user_id in ADMINS:
            views = movie.get("views", 0)
            caption += f"\n\n📥 Yuklanganlar: {views}"

        # ✅ Videoni yuboramiz
        sent = await message.answer_video(
            video=movie["file_id"],
            caption=caption
        )

        # ✅ Ogohlantirishni yuboramiz (videodan keyin)
        warning = (
            "⏱️ Muayyan muammolar tufayli bot tomonidan yuborilgan kinolar 60 soniyadan so‘ng o‘chiriladi.\n\n"
            "✅ Kinoni doʻstlaringizga yoki saqlangan xabarlarga yuboring va yuklab oling.\n\n"
            "🙂 Noqulaylik uchun uzr — @TheMovieUz_bot"
        )
        warning_msg = await message.answer(warning)

        # ✅ 60 soniyadan keyin kino xabarini o‘chiramiz
        await asyncio.sleep(60)
        try:
            await bot.delete_message(message.chat.id, sent.message_id)
        except:
            pass
        try:
            await bot.delete_message(message.chat.id, warning_msg.message_id)
        except:
            pass

    else:
        await message.answer("❌ Bunday kino topilmadi.")

def get_admin_panel():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📥 Kino qo'shish"), KeyboardButton(text="📤 Kino o'chirish")],
            [KeyboardButton(text="➕ Admin qo'shish"), KeyboardButton(text="❌ Admin o'chirish")],
            [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="📢 Reklama yuborish")],
            [KeyboardButton(text="⚙️ Majburiy a'zolik sozlamalari")],
            [KeyboardButton(text=f"🔁 A'zolik holati: {'✅ ON' if force_sub else '❌ OFF'}")]
        ],
        resize_keyboard=True
    )
@router.message(F.text == "⬅️ Orqaga")
async def go_back(message: Message):
    await message.answer("📋 Admin panelga qaytdingiz", reply_markup=get_admin_panel())



@router.message(F.text == "📥 Kino qo'shish")
async def start_add_movie(message: Message, state: FSMContext):
    await state.clear()
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="cancel_add_movie")]
    ])
    await message.answer("🎬 Kino kodi (3 yoki 4 xonali raqam) kiriting:", reply_markup=markup)
    await state.set_state(AddMovie.waiting_for_code)


@router.message(AddMovie.waiting_for_code)
async def ask_video(message: Message, state: FSMContext):
    code = message.text.strip()
    if not code.isdigit():
        await message.answer("❗ Kod faqat raqam bo‘lishi kerak.")
        return
    if code in MOVIES:
        await message.answer("❗ Bu kod allaqachon mavjud.")
        return
    await state.update_data(code=code)
    await state.set_state(AddMovie.waiting_for_description)
    await message.answer("📝 Kino tavsifini kiriting:")
    
@router.message(AddMovie.waiting_for_description)
async def get_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await state.set_state(AddMovie.waiting_for_video)
    await message.answer("📽 Iltimos, kino videosini yuboring:")


@router.message(AddMovie.waiting_for_video)
async def get_video(message: Message, state: FSMContext):
    if not message.video:
        return await message.answer("❗ Iltimos, faqat video yuboring!")

    data = await state.get_data()
    code = data.get("code")
    description = data.get("description")
    file_id = message.video.file_id

    MOVIES[code] = {
        "file_id": file_id,
        "description": description
    }
    save_data()
    await message.answer(f"✅ Kino saqlandi!\nKod: <code>{code}</code>")
    await state.clear()

@router.callback_query(F.data == "cancel_add_movie")
async def cancel_add_movie(call: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await call.message.delete()
    except:
        pass
    await call.message.answer("❌ Bekor qilindi.", reply_markup=get_admin_panel())

@router.message(F.text == "📤 Kino o'chirish")
async def delete_movie(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(DeleteMovie.waiting_for_code)
    await message.answer("❌ O‘chirmoqchi bo‘lgan kino kodini yuboring:")

@router.message(DeleteMovie.waiting_for_code)
async def confirm_delete_movie(message: Message, state: FSMContext):
    code = message.text.strip()
    if code in MOVIES:
        del MOVIES[code]
        save_data()
        await message.answer(f"✅ {code} kodi o‘chirildi.")
    else:
        await message.answer("🚫 Bunday kod topilmadi.")
    await state.clear()


@router.message(F.text == "📊 Statistika")

async def show_stats(message: Message, state: FSMContext):
    await state.clear()

    total, active = count_users()
    new_24 = count_new_24h()
    new_7 = count_new_7d()
    new_30 = count_new_30d()
    movies = total_movies_count()
    now_str = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

    await message.answer(
        f"👥 Umumiy foydalanuvchilar: <b>{total}</b>\n"
        f"🟢 Faollari: <b>{active}</b>\n"
        f"📈 24 soatda: <b>{new_24}</b>\n"
        f"📅 7 kunda: <b>{new_7}</b>\n"
        f"📆 30 kunda: <b>{new_30}</b>\n"
        f"🎬 Jami kinolar: <b>{movies}</b>\n\n"
        f"🕓 <i>{now_str}</i>",
        parse_mode=ParseMode.HTML
    )

@router.message(F.text == "📢 Reklama yuborish")
async def ask_ad_message(message: Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        await message.answer("🚫 Sizda ruxsat yo'q.")
        return
    await message.answer("✉️ Reklama matnini yoki rasm/video bilan yuboring:")
    await state.set_state(AdBroadcast.waiting_for_content)

@router.message(AdBroadcast.waiting_for_content)
async def handle_ad_content(message: Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        return
    if message.text and message.text.startswith("http"):
        await state.update_data(link=message.text)
        await message.answer("❗ Endi izohli matnni ham yuboring:")
        await state.set_state(AdBroadcast.waiting_for_text_with_link)
    else:
        await send_ad_to_all(message)
        await state.clear()

@router.message(AdBroadcast.waiting_for_text_with_link)
async def handle_ad_caption(message: Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        return
    data = await state.get_data()
    link = data.get("link", "")
    text = f"{message.text}\n\n{link}"
    await send_ad_to_all(message, override_text=text)
    await state.clear()

async def send_ad_to_all(message: Message, override_text: str = None):
    total, errors = 0, 0
    status_msg = await message.answer("📤 Reklama yuborilmoqda, iltimos kuting...")

    for uid in list(USERS.keys()):
        try:
            uid_int = int(uid)
            if override_text:
                await message.bot.send_message(uid_int, override_text)
            elif message.photo:
                await message.bot.send_photo(uid_int, message.photo[-1].file_id, caption=message.caption or "")
            elif message.video:
                await message.bot.send_video(uid_int, message.video.file_id, caption=message.caption or "")
            elif message.text:
                await message.bot.send_message(uid_int, message.text)
            total += 1
        except Exception as e:
            print(f"Xato foydalanuvchi {uid}: {e}")
            errors += 1
        await asyncio.sleep(0.01)

    await status_msg.edit_text(f"✅ Yuborildi: {total} ta\n❌ Xatolik: {errors} ta")
 
    
@router.message(F.text == "⚙️ Majburiy a'zolik sozlamalari")
async def show_subscription_settings(message: Message):
    markup = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Kanal ulash"), KeyboardButton(text="➖ Kanal uzish")],
            [KeyboardButton(text="📋 Kanallar ro'yxati"), KeyboardButton(text="🤖 Botlar ro'yxati")],
            [KeyboardButton(text="➕ Bot qo'shish"), KeyboardButton(text="➖ Bot uzish")],
            [KeyboardButton(text="📽 Kinolar ro'yxati")],
            [KeyboardButton(text="⬅️ Orqaga")]
        ],
        resize_keyboard=True
    )
    await message.answer("⚙️ Majburiy a'zolik sozlamalari menyusi:", reply_markup=markup)
   

# --- Kanal ulash tugmasi ---
@router.message(F.text == "➕ Kanal ulash")
async def choose_channel_type(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔓 Public kanal", callback_data="add_public")],
        [InlineKeyboardButton(text="🔐 Private kanal", callback_data="add_private")]
    ])
    await message.answer("Qanday turdagi kanal qo‘shmoqchisiz?", reply_markup=keyboard)

# --- Public kanal qo‘shish ---
@router.callback_query(F.data == "add_public")
async def add_public_channel_prompt(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("🔗 Public kanal havolasini yuboring (masalan: https://t.me/yourchannel):")
    await state.set_state(SubSettings.public_channel_add)

@router.message(SubSettings.public_channel_add)
async def save_public_channel(message: Message, state: FSMContext):
    url = normalize_url(message.text)
    if url.startswith("https://t.me/") and "joinchat" not in url and "+" not in url:
        if not any(normalize_url(ch["url"]) == url for ch in channels):
            channels.append({"url": url, "type": "public"})
            save_data()
            await message.answer("✅ Public kanal qo‘shildi.")
        else:
            await message.answer("⚠ Bu kanal allaqachon mavjud.")
    else:
        await message.answer("❌ Noto‘g‘ri public kanal havolasi.")
    await state.clear()

# --- Private kanal qo‘shish ---
@router.callback_query(F.data == "add_private")
async def add_private_channel_prompt(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text(
        "🔐 <b>Private kanalni qo‘shish uchun quyidagi bosqichlarni bajaring:</b>\n\n"
        "1. Birinchi bo‘lib <b>botni</b> (@TheMovieUz_bot) <b>kanalingizga administrator</b> qilib qo‘shing.\n"
        "2. <b>kanaldan istalgan postni forward</b> qilib yuboring.\n\n",
        parse_mode="HTML"
    )
    await state.set_state(SubSettings.private_channel_add)

@router.message(F.forward_from_chat)
async def add_channel_from_forwarded_post(message: Message, state: FSMContext):
    chat = message.forward_from_chat
    if chat.type != "channel":
        await message.answer("❌ Faqat kanaldan yuborilgan postni jo‘nating.")
        return

    channel_id = chat.id
    channel_title = chat.title
    username = chat.username
    url = f"https://t.me/{username}" if username else "PRIVATE"

    if any(ch.get("id") == channel_id for ch in channels):
        await message.answer("⚠ Bu kanal allaqachon mavjud.")
        return

    if url == "PRIVATE":
        await state.update_data(id=channel_id)
        await message.answer("🔗 Bu private kanal. Endi kanal havolasini yuboring (https://t.me/+...):")
        await state.set_state(SubSettings.private_channel_manual_url)
    else:
        channels.append({"url": url, "id": channel_id, "type": "public"})
        save_data()
        await message.answer(f"✅ Public kanal qo‘shildi:\n📢 {channel_title}\n🔗 {url}")

@router.message(SubSettings.private_channel_manual_url)
async def save_private_channel_url(message: Message, state: FSMContext):
    text = message.text.strip()
    
    if not text.startswith("https://t.me/+") and "joinchat" not in text:
        await message.answer("❌ Noto‘g‘ri private kanal havolasi.")
        return

    data = await state.get_data()
    channel_id = data.get("id")

    channels.append({
        "url": text,
        "id": channel_id,
        "type": "private"
    })
    save_data()

    # Join requestni tayyorlab qo‘shamiz
    file_path = "join_requests.json"
    if not os.path.exists(file_path):
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump({}, f)

    with open(file_path, "r+", encoding="utf-8") as f:
        try:
            join_data = json.load(f)
        except json.JSONDecodeError:
            join_data = {}

        if str(channel_id) not in join_data:
            join_data[str(channel_id)] = []

        f.seek(0)
        json.dump(join_data, f, indent=2, ensure_ascii=False)
        f.truncate()

    await message.answer("✅ Private kanal qo‘shildi.")
    await state.clear()

    
# --- Kanal turini tanlash ---
@router.message(F.text == "➖ Kanal uzish")
async def choose_channel_type_to_delete(message: Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="🌐 Public kanallar", callback_data="del_channel:public")
    builder.button(text="🔒 Private kanallar", callback_data="del_channel:private")
    builder.adjust(1)
    await message.answer("🗑 Qaysi turdagi kanallarni o‘chirmoqchisiz?", reply_markup=builder.as_markup())

# --- Tanlangan turdagi kanallarni ko‘rsatish ---
@router.callback_query(F.data.startswith("del_channel:"))
async def show_channels_by_type(call: CallbackQuery):
    ch_type = call.data.split(":")[1]
    filtered = [(i, ch) for i, ch in enumerate(channels) if ch.get("type") == ch_type]

    if not filtered:
        await call.message.edit_text(f"🚫 Hech qanday {ch_type.upper()} kanal topilmadi.")
        return

    builder = InlineKeyboardBuilder()
    text = f"🗑 {ch_type.upper()} kanallar ro‘yxati:\n\n"
    for i, ch in filtered:
        text += f"{i+1}. {ch['url']}\n"
        builder.button(text=f"❌ {i+1}", callback_data=f"remove_channel_idx:{i}")
    builder.adjust(1)
    await call.message.edit_text(text=text, reply_markup=builder.as_markup())

# --- Kanalni o‘chirish ---
@router.callback_query(F.data.startswith("remove_channel_idx:"))
async def remove_selected_channel(call: CallbackQuery):
    idx = int(call.data.split(":")[1])
    try:
        removed = channels.pop(idx)
        save_data()

        # 🔁 Faqat ID bor bo‘lsa o‘chirish
        if "id" in removed:
            remove_channel_from_join_requests(str(removed["id"]))
        else:
            print("⚠️ Kanal ID yo‘q, faqat channels ro‘yxatidan o‘chirildi")

        await call.message.edit_text(f"✅ {removed['type'].upper()} kanal o‘chirildi:\n🔗 {removed['url']}")
    except IndexError:
        await call.answer("❌ Bunday kanal topilmadi.", show_alert=True)

# --- join_requests.json dan ham o‘chirish ---
def remove_channel_from_join_requests(channel_id: str):
    file_path = "join_requests.json"

    if not os.path.exists(file_path):
        return

    with open(file_path, "r+", encoding="utf-8") as f:
        try:
            data = json.load(f)
            if channel_id in data:
                del data[channel_id]
                f.seek(0)
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.truncate()
        except json.JSONDecodeError:
            pass


@router.message(F.text == "📋 Kanallar ro'yxati")
async def show_channel_type_buttons(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 Public", callback_data="list_public")],
        [InlineKeyboardButton(text="🔒 Private", callback_data="list_private")]
    ])
    await message.answer("Qaysi turdagi kanallarni ko‘rmoqchisiz?", reply_markup=keyboard)

@router.callback_query(F.data == "list_public")
async def list_public_channels(callback: CallbackQuery):
    public_channels = [ch["url"] for ch in channels if ch.get("type") == "public"]

    if not public_channels:
        await safe_edit(callback, "🚫 Hech qanday Public kanal mavjud emas.")
        return

    text = "🌐 <b>Public kanallar roʻyxati:</b>\n\n"
    text += "\n".join(f"{i+1}. {url}" for i, url in enumerate(public_channels))

    await safe_edit(callback, text)

async def safe_edit(callback: CallbackQuery, text: str):
    try:
        await callback.message.edit_text(text, parse_mode="HTML")
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await callback.answer("🔁 Xabar allaqachon ko‘rsatilgan.")
        else:
            raise



@router.callback_query(F.data == "list_private")
async def list_private_channels(callback: CallbackQuery):
    private_channels = [ch["url"] for ch in channels if ch.get("type") == "private"]

    if not private_channels:
        await safe_edit(callback, "🚫 Hech qanday Private kanal mavjud emas.")
        return

    text = "🔒 <b>Private kanallar roʻyxati:</b>\n\n"
    text += "\n".join(f"{i+1}. {url}" for i, url in enumerate(private_channels))

    await safe_edit(callback, text)

@router.message(F.text == "➕ Bot qo‘shish")
async def ask_bot_info(message: Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        return
    await message.answer("🤖 Bot nomini yuboring:")
    await state.set_state("get_bot_name")


@router.message(F.state == "get_bot_name")
async def get_bot_name(message: Message, state: FSMContext):
    await state.update_data(bot_name=message.text)
    await message.answer("🔗 Endi bot havolasini yuboring:")
    await state.set_state("get_bot_url")


@router.message(F.state == "get_bot_url")
async def get_bot_url(message: Message, state: FSMContext):
    data = await state.get_data()
    bot_name = data["bot_name"]
    bot_url = message.text

    bots.append({"name": bot_name, "url": bot_url})
    save_data()
    await message.answer(f"✅ {bot_name} qo‘shildi!", reply_markup=get_admin_panel())
    await state.clear()
    
# --- Bot uzish ---
@router.message(F.text == "➖ Bot uzish")
async def remove_bot(message: Message, state: FSMContext):
    if not bots:
        await message.answer("🚫 Bot ro'yxati bo‘sh.")
        return

    msg = "🗑 O‘chirmoqchi bo‘lgan bot raqamini yuboring:\n"
    for i, b in enumerate(bots):
        msg += f"{i + 1}. {b.get('name', b.get('url', 'Nomaʼlum bot'))}\n"

    await message.answer(msg)
    await state.set_state(SubSettings.bot_remove)

@router.message(SubSettings.bot_remove)
async def bot_remove_confirm(message: Message, state: FSMContext):
    try:
        index = int(message.text.strip()) - 1
        if 0 <= index < len(bots):
            removed = bots.pop(index)
            save_data()
            name = removed.get("name", removed.get("url", "Nomaʼlum bot"))
            await message.answer(f"✅ O‘chirildi: <b>{name}</b>", parse_mode="HTML")
        else:
            await message.answer("🚫 Noto‘g‘ri raqam.")
    except ValueError:
        await message.answer("🚫 Iltimos, faqat raqam kiriting.")
    await state.clear()
    
@router.message(F.text == "🤖 Botlar ro‘yxati")
async def list_bots(message: Message):
    if not bots:
        await message.answer("🤖 Hozircha hech qanday bot qo‘shilmagan.")
        return

    text = "🤖 Botlar ro‘yxati:\n\n"
    for b in bots:
        text += f"🔹 <a href=\"{b['url']}\">{b['name']}</a>\n"
    await message.answer(text, parse_mode="HTML")
       
@router.message(F.text == "➕ Admin qo'shish")
async def add_admin_prompt(message: Message, state: FSMContext):
    await message.answer("🆔 Yangi admin ID raqamini yuboring:")
    await state.set_state(AdminManage.add)

@router.message(AdminManage.add)
async def add_admin(message: Message, state: FSMContext):
    try:
        new_admin = int(message.text.strip())
        if new_admin in ADMINS:
            await message.answer("⚠️ Bu admin allaqachon ro‘yxatda.")
        else:
            ADMINS.append(new_admin)
            save_data()
            await message.answer(f"✅ {new_admin} ID admin sifatida qo‘shildi.")
    except ValueError:
        await message.answer("🚫 Noto‘g‘ri ID. Raqam kiriting.")
    await state.clear()

# Adminni o‘chirish uchun tugma bosilganda
@router.message(F.text == "❌ Admin o'chirish")
async def remove_admin_prompt(message: Message, state: FSMContext):
    await message.answer("🆔 O‘chirmoqchi bo‘lgan admin ID raqamini yuboring:")
    await state.set_state(AdminManage.remove)

# Adminni o‘chirish jarayoni
@router.message(AdminManage.remove)
async def remove_admin(message: Message, state: FSMContext):
    try:
        admin_id = int(message.text.strip())
        
        if admin_id not in ADMINS:
            await message.answer("🚫 Bu ID ro'yxatda mavjud emas.")
        
        elif admin_id == SUPER_ADMIN_ID:
            await message.answer("🚫 Super adminni o‘chirish mumkin emas.")
        
        elif len(ADMINS) == 1:
            await message.answer("⚠️ Kamida bitta admin bo‘lishi kerak.")
        
        else:
            ADMINS.remove(admin_id)
            save_data()
            await message.answer(f"✅ {admin_id} ID admin o‘chirildi.")

            # Agar foydalanuvchi o‘zini o‘chirgan bo‘lsa, panelni olib tashlaymiz
            if message.from_user.id == admin_id:
                await message.answer("ℹ️ Siz endi oddiy foydalanuvchisiz.", reply_markup=ReplyKeyboardRemove())
    
    except ValueError:
        await message.answer("🚫 Noto‘g‘ri ID. Raqam kiriting.")
    
    await state.clear()
@router.message(F.text == "🎬 Kinolar ro'yxati")
async def show_movies_list(message: Message):
    movies = data.get("movies", {})
    if not movies:
        await message.answer("🚫 Kinolar ro'yxati bo‘sh.")
        return
    
    msg = "🎬 Kinolar ro'yxati:\n\n"
    for code, movie in movies.items():
        desc = movie.get("description", "Ta'rif mavjud emas")
        msg += f"🎥 Kod: <b>{code}</b>\n📄 Tavsif: {desc}\n\n"    
    await message.answer(msg, parse_mode="HTML")

@router.callback_query(F.data == "cleanup_join_requests")
async def handle_cleanup_join_requests(call: CallbackQuery):
    success = clean_join_request_urls()
    if success:
        await call.answer("✅ Join request URL lar tozalandi!", show_alert=True)
    else:
        await call.answer("🚫 Tozalashda xatolik yoki fayl topilmadi!", show_alert=True)
        
@router.message(F.text == "🧹 Join tozalash")
async def clean_join_requests_handler(message: Message):
    count = clean_join_requests_file()
    await message.answer(f"✅ Join request fayli tozalandi. {count} ta kanal optimallashtirildi.")
 

def get_movie_by_code(message):
    code = message.text.strip()
    user_id = message.from_user.id
    update_user(user_id)
    
async def remove_user_admin_panel(user_id: int):
    # Misol uchun, admins ro'yxatidan user_id ni o'chirish
    if user_id in ADMINS:
        ADMINS.remove(user_id)
        save_data()  # Saqlash funksiyasi, o'zingizda mavjud bo'lishi kerak


@router.message(lambda m: m.text and m.text.startswith("🔁 A'zolik holati"))
async def toggle_force_sub(message: Message):
    global force_sub
    force_sub = not force_sub
    save_data()
    await message.answer(
        f"Majburiy a'zolik holati endi: {'✅ ON' if force_sub else '❌ OFF'}",
        reply_markup=get_admin_panel()
    )


# Routerni Dispatcherga qo‘shish
dp.include_router(router)

# Botni ishga tushirish
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
