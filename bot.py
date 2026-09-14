 import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

TOKEN = "8889750976:AAFxkTtCjF_ICnP3zuLby6s518dt1D0EUkU"

logging.basicConfig(level=logging.INFO)
router = Router()

# --- BAZA BILAN ISHLASH ---
def init_db():
    conn = sqlite3.connect("arm_database.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dispatchers (
            user_id INTEGER PRIMARY KEY
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            book TEXT,
            name TEXT,
            faculty TEXT,
            phone TEXT,
            location_info TEXT,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def add_dispatcher(user_id: int):
    conn = sqlite3.connect("arm_database.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO dispatchers (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def get_dispatchers():
    conn = sqlite3.connect("arm_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM dispatchers")
    rows = cursor.fetchall()
    conn.close()
    
    # Bazadan tashqari, doimiy asosiy dispetcher ID raqamini ham shu yerga qo'shamiz (7091086144)
    default_admins = [7091086144]
    db_admins = [row[0] for row in rows]
    
    # Hammasini birlashtirib, takrorlanmaydigan qilib qaytaramiz
    return list(set(default_admins + db_admins))

def save_order(student_id: int, book: str, name: str, faculty: str, phone: str, location_info: str):
    conn = sqlite3.connect("arm_database.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO orders (student_id, book, name, faculty, phone, location_info, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
    """, (student_id, book, name, faculty, phone, location_info, "🟡 Yangi buyurtma qabul qilindi"))
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return order_id

def update_order_status(order_id: int, status: str):
    conn = sqlite3.connect("arm_database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status = ? WHERE order_id = ?", (status, order_id))
    conn.commit()
    cursor.execute("SELECT student_id FROM orders WHERE order_id = ?", (order_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def get_order_stats():
    conn = sqlite3.connect("arm_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM orders WHERE date(created_at) = date('now', 'localtime')")
    today_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM orders WHERE datetime(created_at) >= datetime('now', '-7 days', 'localtime')")
    week_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM orders WHERE datetime(created_at) >= datetime('now', '-30 days', 'localtime')")
    month_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM orders")
    total_count = cursor.fetchone()[0]
    conn.close()
    return today_count, week_count, month_count, total_count

# FSM holatlari
class OrderState(StatesGroup):
    book = State()
    name = State()
    faculty = State()
    phone = State()
    location = State()

# Asosiy menyu
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📚 Kitob buyurtma qilish"), KeyboardButton(text="📦 Buyurtmam holati")],
        [KeyboardButton(text="🌐 Elektron katalog (lib.tiet.uz)")],
        [KeyboardButton(text="📝 ARM ga obuna bo'lish (arm.tdmau.uz)")],
        [KeyboardButton(text="ℹ️ Xizmat haqida"), KeyboardButton(text="☎️ Aloqa")]
    ],
    resize_keyboard=True
)

@router.message(CommandStart())
async def start_cmd(message: Message, state: FSMContext):
    await state.clear()
    init_db()
    # Har safar start bosganda asosiy dispetcherni bazaga ham avtomatik qo'shib qo'yamiz
    add_dispatcher(7091086144)
    await message.answer(
        "👋 Assalomu alaykum! Termiz davlat muhandislik va agrotexnologiyalar universiteti "
        "“Inklyuziv ARM” xizmatiga xush kelibsiz. Kerakli bo‘limni tanlang:",
        reply_markup=main_menu
    )

@router.message(Command("addadmin"))
async def add_admin_cmd(message: Message):
    add_dispatcher(message.from_user.id)
    await message.answer("✅ Siz muvaffaqiyatli ARM dispetcheri etib ro'yxatdan o'tdingiz!\nStatistika uchun /stats buyrug'idan foydalanishingiz mumkin.")

@router.message(Command("stats"))
async def stats_cmd(message: Message):
    if message.from_user.id not in get_dispatchers():
        await message.answer("Bu buyruq faqat dispetcherlar uchun.")
        return
    
    today, week, month, total = get_order_stats()
    await message.answer(
        "📊 <b>ARM Buyurtmalar Statistikasi</b>\n\n"
        f"📅 Bugungi buyurtmalar: <b>{today} ta</b>\n"
        f"📅 Haftalik buyurtmalar (7 kun): <b>{week} ta</b>\n"
        f"📅 Oylik buyurtmalar (30 kun): <b>{month} ta</b>\n"
        f"📚 Jami buyurtmalar: <b>{total} ta</b>",
        parse_mode="HTML"
    )

@router.message(F.text == "🌐 Elektron katalog (lib.tiet.uz)")
async def open_catalog(message: Message):
    catalog_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗 lib.tiet.uz saytiga o'tish", url="http://lib.tiet.uz")]
        ]
    )
    await message.answer(
        "📚 Termiz davlat muhandislik va agrotexnologiyalar universiteti elektron kutubxona katalogiga o'tish uchun quyidagi tugmani bosing:",
        reply_markup=catalog_kb
    )

@router.message(F.text == "📝 ARM ga obuna bo'lish (arm.tdmau.uz)")
async def open_subscription(message: Message):
    sub_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗 arm.tdmau.uz saytiga o'tish", url="https://arm.tdmau.uz")]
        ]
    )
    await message.answer(
        "📝 Termiz davlat muhandislik va agrotexnologiyalar universiteti Axborot-resurs markaziga obuna bo'lish va ro'yxatdan o'tish uchun quyidagi tugmani bosing:",
        reply_markup=sub_kb
    )

@router.message(F.text == "ℹ️ Xizmat haqida")
async def about_service(message: Message):
    await message.answer(
        "ℹ️ <b>Inklyuziv ARM xizmati haqida:</b>\n\n"
        "Ushbu bot Termiz davlat muhandislik va agrotexnologiyalar universiteti talabalari va professor-o'qituvchilariga "
        "kutubxona resurslaridan foydalanishni osonlashtirish, kitob buyurtma qilish va masofadan turib xizmat ko'rsatish uchun yaratilgan.",
        parse_mode="HTML"
    )

@router.message(F.text == "☎️ Aloqa")
async def contact_service(message: Message):
    await message.answer(
        "☎️ <b>Bog'lanish uchun:</b>\n\n"
        "🏛 Maskani: Termiz davlat muhandislik va agrotexnologiyalar universiteti, Axborot-resurs markazi.\n"
        "🌐 Veb-sayt: https://arm.tdmau.uz",
        parse_mode="HTML"
    )

@router.message(F.text == "📦 Buyurtmam holati")
async def check_status(message: Message):
    conn = sqlite3.connect("arm_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT order_id, book, status, created_at FROM orders WHERE student_id = ? ORDER BY order_id DESC LIMIT 1", (message.from_user.id,))
    order = cursor.fetchone()
    conn.close()
    
    if order:
        await message.answer(
            f"🆔 <b>Buyurtma №{order[0]:03d}</b>\n"
            f"📚 Kitob: {order[1]}\n"
            f"📊 Holati: {order[2]}\n"
            f"🕐 Vaqti: {order[3]}",
            parse_mode="HTML"
        )
    else:
        await message.answer("Sizda hozircha faol buyurtmalar yo'q.")

# --- QADAM-BAQADAM BUYURTMA BERISH ---
@router.message(F.text == "📚 Kitob buyurtma qilish")
async def order_book(message: Message, state: FSMContext):
    await state.set_state(OrderState.book)
    await message.answer("1️⃣ Kerakli kitob nomini yoki muallifini kiriting:", reply_markup=ReplyKeyboardRemove())

@router.message(OrderState.book)
async def process_book(message: Message, state: FSMContext):
    await state.update_data(book=message.text)
    await state.set_state(OrderState.name)
    await message.answer("2️⃣ Iltimos, F.I.Sh. (Familiya Ism Sharif) ingizni to'liq kiriting:")

@router.message(OrderState.name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(OrderState.faculty)
    await message.answer("3️⃣ Qaysi fakultet va kursda o'qiysiz? (Masalan: Agrotexnologiya, 2-kurs):")

@router.message(OrderState.faculty)
async def process_faculty(message: Message, state: FSMContext):
    await state.update_data(faculty=message.text)
    await state.set_state(OrderState.phone)
    
    phone_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📞 Telefon raqamimni yuborish", request_contact=True)]],
        resize_keyboard=True
    )
    await message.answer("4️⃣ Bog'lanish uchun telefon raqamingizni yuboring (tugmani bosing yoki raqamni yozing):", reply_markup=phone_kb)

@router.message(OrderState.phone)
async def process_phone(message: Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else message.text
    await state.update_data(phone=phone)
    await state.set_state(OrderState.location)
    
    loc_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📍 Lokatsiyani yuborish", request_location=True)]],
        resize_keyboard=True
    )
    await message.answer("5️⃣ Kitobni yetkazib berish uchun lokatsiyangizni yuboring (tugmani bosing yoki manzilni matn ko'rinishida yozing):", reply_markup=loc_kb)

@router.message(OrderState.location)
async def process_location(message: Message, state: FSMContext):
    data = await state.get_data()
    student_id = message.from_user.id
    
    if message.location:
        loc_info = f"GPS: {message.location.latitude}, {message.location.longitude}"
        has_location_obj = True
        lat = message.location.latitude
        lon = message.location.longitude
    else:
        loc_info = message.text
        has_location_obj = False
    
    order_id = save_order(student_id, data['book'], data['name'], data['faculty'], data['phone'], loc_info)
    
    await message.answer(
        f"✅ <b>Buyurtmangiz muvaffaqiyatli qabul qilindi!</b>\n\n"
        f"🆔 Buyurtma raqami: <b>№{order_id:03d}</b>\n"
        f"📚 Kitob: {data['book']}\n"
        f"👤 F.I.Sh.: {data['name']}\n"
        f"🎓 Fakultet: {data['faculty']}\n"
        f"📞 Telefon: {data['phone']}\n"
        f"📍 Manzil: {loc_info}\n\n"
        "🟡 Holati: ARM dispetcherlariga yuborildi.",
        reply_markup=main_menu,
        parse_mode="HTML"
    )
    await state.clear()
    
    dispatcher_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Qabul qilish", callback_data=f"acc_{order_id}"),
                InlineKeyboardButton(text="📚 Kitob tayyor", callback_data=f"rdy_{order_id}")
            ],
            [
                InlineKeyboardButton(text="🚚 Yetkazilmoqda", callback_data=f"del_{order_id}"),
                InlineKeyboardButton(text="✅ Yetkazildi", callback_data=f"don_{order_id}")
            ],
            [
                InlineKeyboardButton(text="🔁 Kitob qaytarib olindi", callback_data=f"ret_{order_id}"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"can_{order_id}")
            ]
        ]
    )

    dispatcher_text = (
        f"🔔 <b>YANGI BUYURTMA №{order_id:03d}</b>\n\n"
        f"📚 Kitob: {data['book']}\n"
        f"👤 F.I.Sh.: {data['name']}\n"
        f"🎓 Fakultet: {data['faculty']}\n"
        f"📞 Telefon: {data['phone']}\n"
        f"📍 Manzil/Lokatsiya: {loc_info}"
    )
    
    dispatchers = get_dispatchers()
    for disp_id in dispatchers:
        try:
            await message.bot.send_message(chat_id=disp_id, text=dispatcher_text, parse_mode="HTML")
            if has_location_obj:
                await message.bot.send_location(chat_id=disp_id, latitude=lat, longitude=lon)
            await message.bot.send_message(chat_id=disp_id, text="Buyurtmani boshqarish:", reply_markup=dispatcher_kb)
        except Exception as e:
            logging.error(f"Dispetcherga yuborishda xatolik: {e}")

# --- DISPETCHER BOSHQARUVI ---
@router.callback_query(F.data.regexp(r"^(acc|rdy|del|don|ret|can|rcv)_(\d+)$"))
async def process_dispatcher_action(callback: CallbackQuery):
    parts = callback.data.split("_")
    action = parts[0]
    order_id = int(parts[1])
    
    if action == "rcv":
        update_order_status(order_id, "✅ Kitob kitobxon tomonidan qabul qilib olindi")
        await callback.message.edit_text(f"{callback.message.text}\n\n<b>Holat:</b> Kitobxon qabul qilib oldi (Buyurtma yakunlandi).", parse_mode="HTML")
        await callback.answer("Tasdiqlandi!")
        return

    status_map = {
        "acc": ("✅ Buyurtma qabul qilindi. Kitob tayyorlanmoqda.", f"✅ Buyurtmangiz (№{order_id:03d}) ARM xodimi tomonidan qabul qilindi. Kitob tayyorlanmoqda."),
        "rdy": ("📚 Kitob tayyor! Yetkazish boshlanmoqda.", f"📚 Kitobingiz (№{order_id:03d}) tayyorlandi. Yetkazib berish jarayoni boshlanadi."),
        "del": ("🚚 Kitob yetkazilmoqda.", f"🚚 Kitobingiz (№{order_id:03d}) ko'rsatilgan manzilga yetkazilmoqda."),
        "don": ("✅ Kitob yetkazib berildi. Talabaning tasdiqlashi kutilmoqda.", f"✅ Kitobingiz (№{order_id:03d}) yetkazib berildi. Iltimos, kitobni olganingizni tasdiqlang:"),
        "ret": ("🔁 Kitob ARMga qaytarib olindi (Yopildi).", f"🔁 Buyurtma (№{order_id:03d}) bo'yicha kitob ARMga muvaffaqiyatli qaytarib olindi. Xizmatingiz uchun rahmat!"),
        "can": ("❌ Buyurtma bekor qilindi.", f"❌ Afsuski, buyurtmangiz (№{order_id:03d}) bekor qilindi.")
    }
    
    disp_text, student_text = status_map.get(action, ("Holat o'zgardi", "Buyurtma holati o'zgardi"))
    student_id = update_order_status(order_id, disp_text)
    
    dispatcher_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Qabul qilish", callback_data=f"acc_{order_id}"),
                InlineKeyboardButton(text="📚 Kitob tayyor", callback_data=f"rdy_{order_id}")
            ],
            [
                InlineKeyboardButton(text="🚚 Yetkazilmoqda", callback_data=f"del_{order_id}"),
                InlineKeyboardButton(text="✅ Yetkazildi", callback_data=f"don_{order_id}")
            ],
            [
                InlineKeyboardButton(text="🔁 Kitob qaytarib olindi", callback_data=f"ret_{order_id}"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"can_{order_id}")
            ]
        ]
    )
    
    markup_to_use = None if action in ["ret", "can"] else dispatcher_kb

    await callback.message.edit_text(
        f"{callback.message.text}\n\n<b>Joriy holat:</b> {disp_text}",
        parse_mode="HTML",
        reply_markup=markup_to_use
    )
    await callback.answer("Holat yangilandi!")
    
    if student_id:
        try:
            if action == "don":
                received_kb = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="✅ Kitobni qabul qilib oldim", callback_data=f"rcv_{order_id}")]
                    ]
                )
                await callback.bot.send_message(chat_id=student_id, text=student_text, reply_markup=received_kb)
            else:
                await callback.bot.send_message(chat_id=student_id, text=student_text)
        except Exception as e:
            logging.error(f"Talabaga xabar yuborishda xatolik: {e}")

async def main():
    init_db()
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    
    await bot.set_my_commands([])
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
