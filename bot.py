from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.sqlite import SQLiteStorage
from aiogram.dispatcher import FSMContext
from aiogram.types import InputFile   # ✅ SHART

from config import TOKEN
from products import PRODUCTS
from states import OrderState
from datetime import datetime
from excel import save_to_excel, update_status

from cutlist.optimizer import optimize
from cutlist.sizes import GLASS_SHEETS
from cutlist.render import render


from database import save_order, get_order


bot = Bot(token=TOKEN)

ORDER_COUNTER = 0

dp = Dispatcher(bot, storage=SQLiteStorage("fsm.db"))


# ================= START =================

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message, state: FSMContext):
    await state.finish()

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📦 Mahsulotlar")

    await message.answer(
        "Assalomu alaykum!\n"
        "Xortum oyna buyurtma botiga xush kelibsiz.\n\n"
        "📦 Mahsulotlarimizni ko‘rish uchun tugmani bosing.",
        reply_markup=kb
    )


# ================= MAHSULOTLAR =================

@dp.message_handler(lambda m: m.text == "📦 Mahsulotlar")
async def show_products(message: types.Message):
    kb = types.InlineKeyboardMarkup(row_width=1)

    for pid, product in PRODUCTS.items():
        kb.add(
            types.InlineKeyboardButton(
                text=product["name"],
                callback_data=f"product_{pid}"
            )
        )

    await message.answer(
        "📦 Mahsulotlar ro‘yxati:\n"
        "Kerakli mahsulotni tanlang 👇",
        reply_markup=kb
    )


@dp.callback_query_handler(lambda c: c.data.startswith("product_"))
async def show_product_detail(call: types.CallbackQuery):
    product_id = int(call.data.split("_")[1])
    product = PRODUCTS[product_id]

    caption = (
        f"📦 {product['name']}\n"
        f"💰 Narx: {product['price']:,} so‘m / 1 m²"
    )

    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton(
            text="✅ Tanlash",
            callback_data=f"select_{product_id}"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            text="⬅️ Orqaga",
            callback_data="back_to_products"
        )
    )

    await call.message.delete()
    await call.message.answer_photo(
        photo=product["photo"],
        caption=caption,
        reply_markup=kb
    )
    await call.answer()


@dp.callback_query_handler(lambda c: c.data == "back_to_products")
async def back_to_products(call: types.CallbackQuery):
    await show_products(call.message)
    await call.answer()


# ================= BUYURTMA BOSHLASH =================

@dp.callback_query_handler(lambda c: c.data.startswith("select_"))
async def select_product(call: types.CallbackQuery, state: FSMContext):
    global ORDER_COUNTER
    ORDER_COUNTER += 1

    product_id = int(call.data.split("_")[1])

    now = datetime.now()
    order_date = now.strftime("%d.%m.%Y")
    order_time = now.strftime("%H:%M:%S")

    product = PRODUCTS[product_id]

    await state.update_data(
    order_id=ORDER_COUNTER,
    order_date=order_date,
    order_time=order_time,
    product_id=product_id,
    product_type=product["glass_type"],  # ✅ MUHIM
    sizes=[],
    current_index=1
)


    await call.message.answer(
        f"🆔 Buyurtma raqami: {ORDER_COUNTER}\n"
        f"📅 Sana: {order_date}\n"
        f"⏰ Vaqt: {order_time}\n\n"
        "📐 Nechta o‘lcham bor?\n"
        "🔹 Minimum: 1 ta\n"
        "🔹 Maksimum: 50 ta\n\n"
        "Masalan: 12"
    )

    await OrderState.waiting_for_count.set()
    await call.answer()


# ================= O‘LCHAMLAR SONI =================

@dp.message_handler(state=OrderState.waiting_for_count)
async def get_count(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Iltimos, faqat son kiriting.")
        return

    count = int(message.text)

    if not 1 <= count <= 50:
        await message.answer("❌ O‘lchamlar soni 1 dan 50 gacha bo‘lishi kerak.")
        return

    await state.update_data(total_count=count)

    await message.answer(
        "📏 1-o‘lcham uchun ENINI kiriting (metrda).\n"
        "Masalan: 0.5"
    )

    await OrderState.waiting_for_width.set()


# ================= ENI =================
@dp.message_handler(state=OrderState.waiting_for_width)
async def get_width(message: types.Message, state: FSMContext):
    try:
        width_cm = float(message.text)
        if width_cm <= 0:
            raise ValueError
        width_m = width_cm / 100  # sm -> m
    except:
        await message.answer("❌ Enini santimetrda kiriting. Masalan: 50")
        return

    await state.update_data(current_width=width_m)

    data = await state.get_data()
    idx = data["current_index"]

    await message.answer(
        f"📐 {idx}-o‘lcham uchun BO‘YINI kiriting (sm).\n"
        "Masalan: 120"
    )

    await OrderState.waiting_for_height.set()


# ================= BO‘YI =================
@dp.message_handler(state=OrderState.waiting_for_height)
async def get_height(message: types.Message, state: FSMContext):
    try:
        height_cm = float(message.text)
        if height_cm <= 0:
            raise ValueError
        height_m = height_cm / 100  # sm -> m
    except:
        await message.answer("❌ Bo‘yini santimetrda kiriting. Masalan: 120")
        return

    await state.update_data(current_height=height_m)

    await message.answer(
        "🔢 Bu o‘lchamdan NECHTA dona bor?\n"
        "Masalan: 2"
    )

    await OrderState.waiting_for_quantity.set()


@dp.message_handler(state=OrderState.waiting_for_quantity)
async def get_quantity(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Faqat BUTUN son kiriting. Masalan: 2")
        return

    qty = int(message.text)

    data = await state.get_data()
    w = data["current_width"]
    h = data["current_height"]

    area = round(w * h * qty, 3)

    sizes = data["sizes"]
    sizes.append({
        "w": w,
        "h": h,
        "qty": qty,
        "area": area
    })

    current = data["current_index"]
    total = data["total_count"]

    if current < total:
        await state.update_data(
            sizes=sizes,
            current_index=current + 1
        )
        await message.answer(
            f"📏 {current+1}-o‘lcham ENINI kiriting"
        )
        await OrderState.waiting_for_width.set()
    else:
        await state.update_data(sizes=sizes)
        # 👉 davom etadi (yakun, telefon, admin)


        total_area = round(sum(s["area"] for s in sizes), 3)
        product = PRODUCTS[data["product_id"]]
        total_price = int(total_area * product["price"])

        if total <= 10:
            status = "🟢 Oddiy buyurtma"
        elif total <= 30:
            status = "🟡 Ogohlantirish bilan"
        else:
            status = "🔴 Yirik buyurtma"

        await message.answer(
            "🧾 Buyurtma yakuni:\n\n"
            f"📦 Mahsulot: {product['name']}\n"
            f"📐 O‘lchamlar soni: {total}\n"
            f"📏 Umumiy kvadrat: {total_area} m²\n"
            f"💰 Jami summa: {total_price:,} so‘m\n"
            f"{status}"
        )

        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.add(
            types.KeyboardButton(
                text="📞 Telefon raqamni yuborish",
                request_contact=True
            )
        )

        await message.answer(
            "📞 Iltimos, telefon raqamingizni yuboring:",
            reply_markup=kb
        )

        await OrderState.waiting_for_contact.set()


# ================= TELEFON =================

@dp.message_handler(content_types=types.ContentType.CONTACT,
                    state=OrderState.waiting_for_contact)
async def get_contact(message: types.Message, state: FSMContext):
    data = await state.get_data()

    phone = message.contact.phone_number
    product = PRODUCTS[data["product_id"]]

    sizes_text = ""
    for i, s in enumerate(data["sizes"], 1):
        sizes_text += (
        f"{i}) {s['w']} x {s['h']} × {s['qty']} ta = {s['area']} m²\n"
    )


    total_area = sum(s["area"] for s in data["sizes"])
    total_price = int(total_area * product["price"])

    admin_text = (
        f"📥 YANGI BUYURTMA\n\n"
        f"🆔 Buyurtma: #{data['order_id']}\n"
        f"📅 Sana: {data['order_date']}\n"
        f"⏰ Vaqt: {data['order_time']}\n\n"
        f"📦 Mahsulot: {product['name']}\n\n"
        f"📐 O‘lchamlar:\n{sizes_text}\n"
        f"📏 Umumiy: {total_area} m²\ n"
        f"💰 Summa: {total_price:,} so‘m\n\n"
        f"📞 Telefon: {phone}"
    )

    # ✅ INLINE TUGMALAR SHU YERDA
    admin_kb = types.InlineKeyboardMarkup(row_width=2)
    admin_kb.add(
    types.InlineKeyboardButton(
        text="✅ Qabul qilindi",
        callback_data=f"accept_{data['order_id']}"
    ),
    types.InlineKeyboardButton(
        text="❌ Bekor qilindi",
        callback_data=f"cancel_{data['order_id']}"
    )
)
    admin_kb.add(
    types.InlineKeyboardButton(
        text="📐 CutList",
        callback_data=f"cutlist_{data['order_id']}"
    )
)




    save_to_excel({
    "order_id": data["order_id"],
    "order_date": data["order_date"],
    "order_time": data["order_time"],
    "product_name": product["name"],
    "phone": phone,
    "total_area": total_area,
    "total_price": total_price,
    "status": "Yangi"
})


    from config import ADMINS
    for admin_id in ADMINS:
        await bot.send_message(
            admin_id,
            admin_text,
            reply_markup=admin_kb
        )

    await message.answer(
        "✅ Buyurtmangiz qabul qilindi. Tez orada bog‘lanamiz.",
        reply_markup=types.ReplyKeyboardRemove()
    )

    data = await state.get_data()

    save_order(data["order_id"], data)



    await state.finish()






# ================= CUTLIST (ADMIN) =================

@dp.callback_query_handler(lambda c: c.data.startswith("cutlist_"))
async def admin_cutlist(call: types.CallbackQuery):
    order_id = int(call.data.split("_")[1])

    data = get_order(order_id)
    if not data:
        await call.answer("❌ Buyurtma topilmadi", show_alert=True)
        return

    product = PRODUCTS[data["product_id"]]
    product_type = product["glass_type"]

    sheet = GLASS_SHEETS[product_type]

    pieces = []
    for s in data["sizes"]:
        pieces.append({
            "w": int(s["w"] * 100),
            "h": int(s["h"] * 100),
            "qty": s.get("qty", 1)
        })

    sheets = optimize(sheet["w"], sheet["h"], pieces)

    for i, layout in enumerate(sheets, start=1):
        file = f"cutlist_{order_id}_{i}.png"

        render(sheet["w"], sheet["h"], layout, file)

        await call.message.answer_photo(
            photo=InputFile(file),
            caption=f"📐 CutList #{i}"
        )


    
    await call.answer("CutList tayyor ✅")


# ================= QABUL QILINDI =================

@dp.callback_query_handler(lambda c: c.data.startswith("accept_"))
async def accept_order(call: types.CallbackQuery):
    order_id = call.data.split("_")[1]

    update_status(order_id, "Qabul qilindi")

    await call.message.edit_reply_markup()
    await call.message.reply(
        f"✅ Buyurtma #{order_id} QABUL QILINDI"
    )

    await call.answer("Qabul qilindi")



# ================= bekor qilindi QILINDI =================


@dp.callback_query_handler(lambda c: c.data.startswith("cancel_"))
async def cancel_order(call: types.CallbackQuery):
    order_id = call.data.split("_")[1]

    update_status(order_id, "Bekor qilindi")

    await call.message.edit_reply_markup()
    await call.message.reply(
        f"❌ Buyurtma #{order_id} BEKOR QILINDI"
    )

    await call.answer("Bekor qilindi")

# ================= file-id =================


@dp.message_handler(content_types=types.ContentType.PHOTO)
async def get_photo_id(message: types.Message):
    photo_id = message.photo[-1].file_id
    await message.answer(f"📸 file_id:\n{photo_id}")


# ================= RUN =================

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
