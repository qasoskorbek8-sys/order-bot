from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
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



from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

uri = "mongodb+srv://abdulhakimorifjonov853_db_user:<db_password>@cluster0.rv01c6f.mongodb.net/?appName=Cluster0"

# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

ORDERS = {}


bot = Bot(token=TOKEN)

ORDER_COUNTER = 0

dp = Dispatcher(bot, storage=MemoryStorage())


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

# ================= ADMIN PANEL =================

@dp.message_handler(commands=["admin"])
async def admin_panel(message: types.Message):

    from config import ADMINS

    if message.from_user.id not in ADMINS:
        return

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)

    kb.add("➕ Yangi mahsulot")
    kb.add("✏️ Narxni o‘zgartirish")
    kb.add("🖼 Rasmni o‘zgartirish")
    kb.add("❌ Mahsulotni o‘chirish") 

    await message.answer(
        "⚙️ Admin panel",
        reply_markup=kb
    )


@dp.message_handler(lambda m: m.text == "➕ Yangi mahsulot")
async def add_product(message: types.Message):

    await message.answer("📦 Mahsulot nomini yuboring")

    await OrderState.product_name.set()



@dp.message_handler(state=OrderState.product_name)
async def get_product_name(message: types.Message, state: FSMContext):

    await state.update_data(name=message.text)

    await message.answer("💰 Narxini yuboring")

    await OrderState.product_price.set()

@dp.message_handler(state=OrderState.product_price)
async def get_product_price(message: types.Message, state: FSMContext):

    if not message.text.isdigit():
        await message.answer("❌ Faqat son kiriting")
        return

    await state.update_data(price=int(message.text))

    await message.answer("🖼 Mahsulot rasmini yuboring")

    await OrderState.product_photo.set()



@dp.message_handler(content_types=types.ContentType.PHOTO, state=OrderState.product_photo)
async def get_product_photo(message: types.Message, state: FSMContext):

    photo = message.photo[-1].file_id

    data = await state.get_data()

    PRODUCTS[len(PRODUCTS)+1] = {
        "name": data["name"],
        "price": data["price"],
        "photo": photo
    }

    await message.answer("✅ Mahsulot qo‘shildi")

    await state.finish()


@dp.message_handler(lambda m: m.text == "✏️ Narxni o‘zgartirish")
async def change_price(message: types.Message):

    kb = types.InlineKeyboardMarkup()

    for pid, p in PRODUCTS.items():
        kb.add(
            types.InlineKeyboardButton(
                p["name"],
                callback_data=f"price_{pid}"
            )
        )

    await message.answer(
        "📦 Qaysi mahsulot narxini o‘zgartirmoqchisiz?",
        reply_markup=kb
    )


@dp.callback_query_handler(lambda c: c.data.startswith("price_"))
async def choose_product_for_price(call: types.CallbackQuery, state: FSMContext):

    pid = int(call.data.split("_")[1])

    await state.update_data(product_edit=pid)

    await call.message.answer("💰 Yangi narxni kiriting")

    await OrderState.new_price.set()

    await call.answer()





@dp.message_handler(state=OrderState.new_price)
async def save_new_price(message: types.Message, state: FSMContext):

    if not message.text.isdigit():
        await message.answer("❌ Faqat son kiriting")
        return

    data = await state.get_data()

    pid = data["product_edit"]

    PRODUCTS[pid]["price"] = int(message.text)

    await message.answer("✅ Narx muvaffaqiyatli yangilandi")

    await state.finish()



@dp.message_handler(lambda m: m.text == "❌ Mahsulotni o‘chirish")
async def delete_product(message: types.Message):

    kb = types.InlineKeyboardMarkup()

    for pid, product in PRODUCTS.items():
        kb.add(
            types.InlineKeyboardButton(
                product["name"],
                callback_data=f"delete_{pid}"
            )
        )

    await message.answer(
        "❌ Qaysi mahsulotni o‘chirmoqchisiz?",
        reply_markup=kb
    )



@dp.callback_query_handler(lambda c: c.data.startswith("delete_"))
async def confirm_delete(call: types.CallbackQuery):

    pid = int(call.data.split("_")[1])

    if pid in PRODUCTS:
        name = PRODUCTS[pid]["name"]
        del PRODUCTS[pid]

        await call.message.answer(
            f"❌ {name} mahsuloti o‘chirildi"
        )

    await call.answer()

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

    await state.update_data(
        order_id=ORDER_COUNTER,
        order_date=now.strftime("%d.%m.%Y"),
        order_time=now.strftime("%H:%M:%S"),
        product_id=product_id,
        sizes=[]
    )

    await call.message.answer(
        "📐 O‘lcham kiriting\n\n"
        "➡️ ENINI santimetrda yozing (masalan: 50)"
    )

    await OrderState.width.set()
    await call.answer()


# # ================= O‘LCHAMLAR SONI =================

# @dp.message_handler(state=OrderState.waiting_for_count)
# async def get_count(message: types.Message, state: FSMContext):
#     if not message.text.isdigit():
#         await message.answer("❌ Iltimos, faqat son kiriting.")
#         return

#     count = int(message.text)

#     if not 1 <= count <= 50:
#         await message.answer("❌ O‘lchamlar soni 1 dan 50 gacha bo‘lishi kerak.")
#         return

#     await state.update_data(total_count=count)

#     await message.answer(
#         "📏 1-o‘lcham uchun ENINI kiriting (metrda).\n"
#         "Masalan: 0.5"
#     )

#     await OrderState.waiting_for_width.set()


# ================= ENI =================
# @dp.message_handler(state=OrderState.waiting_for_width)
# async def get_width(message: types.Message, state: FSMContext):
#     try:
#         width_cm = float(message.text)
#         if width_cm <= 0:
#             raise ValueError
#         width_m = width_cm / 100  # sm -> m
#     except:
#         await message.answer("❌ Enini santimetrda kiriting. Masalan: 50")
#         return

#     await state.update_data(current_width=width_m)

#     data = await state.get_data()
#     idx = data["current_index"]

#     await message.answer(
#         f"📐 {idx}-o‘lcham uchun BO‘YINI kiriting (sm).\n"
#         "Masalan: 120"
#     )

#     await OrderState.waiting_for_height.set()


@dp.message_handler(state=OrderState.width)
async def get_width(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Enini santimetrda kiriting")
        return

    await state.update_data(width=int(message.text))

    await message.answer("📐 BO‘YINI santimetrda kiriting")
    await OrderState.height.set()


# ================= BO‘YI =================
# @dp.message_handler(state=OrderState.waiting_for_height)
# async def get_height(message: types.Message, state: FSMContext):
#     try:
#         height_cm = float(message.text)
#         if height_cm <= 0:
#             raise ValueError
#         height_m = height_cm / 100  # sm -> m
#     except:
#         await message.answer("❌ Bo‘yini santimetrda kiriting. Masalan: 120")
#         return

#     await state.update_data(current_height=height_m)

#     await message.answer(
#         "🔢 Bu o‘lchamdan NECHTA dona bor?\n"
#         "Masalan: 2"
#     )

#     await OrderState.waiting_for_quantity.set()


@dp.message_handler(state=OrderState.height)
async def get_height(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Bo‘yini santimetrda kiriting")
        return

    await state.update_data(height=int(message.text))

    await message.answer("🔢 NECHTA dona?")
    await OrderState.qty.set()








@dp.message_handler(state=OrderState.qty)
async def get_qty(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Faqat son kiriting")
        return

    qty = int(message.text)
    data = await state.get_data()

    w = data["width"]
    h = data["height"]

    area = round((w * h * qty) / 10000, 3)

    sizes = data.get("sizes", [])
    sizes.append({
        "w": w,
        "h": h,
        "qty": qty,
        "area": area
    })

    await state.update_data(sizes=sizes)

    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("➕ Yana o‘lcham", callback_data="more"),
        types.InlineKeyboardButton("✅ Tugatish", callback_data="finish")
    )

    total_area = round(sum(s["area"] for s in sizes), 3)

    await message.answer(
    f"✅ {w} x {h} sm × {qty} = {area} m²\n\n"
    f"📏 Hozircha umumiy: {total_area} m²\n\n"
    "Yana o‘lcham qo‘shasizmi?",
    reply_markup=kb
)





@dp.callback_query_handler(lambda c: c.data == "more", state="*")
async def add_more(call: types.CallbackQuery, state: FSMContext):
    await call.answer()

    await call.message.answer(
        "📐 Yangi o‘lcham ENINI kiriting (sm)"
    )

    await OrderState.width.set()
# ================= TELEFON =================

@dp.message_handler(content_types=types.ContentType.CONTACT, state=OrderState.contact)
async def get_contact_by_button(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number
    await finish_order(message, state, phone)
@dp.message_handler(state=OrderState.contact)
async def get_contact_by_text(message: types.Message, state: FSMContext):
    phone = message.text.strip()

    if not phone.startswith("+998") or not phone[1:].isdigit() or len(phone) != 13:
        await message.answer(
            "❌ Telefon noto‘g‘ri.\n\n"
            "To‘g‘ri format:\n+998901234567"
        )
        return

    await finish_order(message, state, phone)


@dp.callback_query_handler(lambda c: c.data == "finish", state="*")
async def finish_sizes(call: types.CallbackQuery, state: FSMContext):
    await call.answer()

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(types.KeyboardButton("📞 Telefon yuborish", request_contact=True))

    await call.message.answer(
        "📞 Telefon raqamingizni yuboring",
        reply_markup=kb
    )

    await OrderState.contact.set()

# ================= YORDAMCHI FUNKSIYA =================

async def finish_order(message: types.Message, state: FSMContext, phone: str):

    data = await state.get_data()
    product = PRODUCTS[data["product_id"]]

    total_area = sum(s["area"] for s in data["sizes"])
    total_price = int(total_area * product["price"])
    

    await state.update_data(phone=phone)
    sizes_text = ""

    for i, s in enumerate(data["sizes"], 1):
        sizes_text += ( f"{i}) {s['w']} x {s['h']} sm × {s['qty']} ta = {s['area']} m²\n"
    )

    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton(
            "📤 Buyurtmani adminga yuborish",
            callback_data="send_to_admin"
        ),
        types.InlineKeyboardButton(
            "✏️ Buyurtmani tahrirlash",
            callback_data="edit_order"
        )
    )

    await message.answer(
    f"📦 Buyurtma yakuni\n\n"
    f"📐 O‘lchamlar:\n"
    f"{sizes_text}\n"
    f"📏 Umumiy maydon: {total_area} m²\n"
    f"💰 Jami summa: {total_price:,} so‘m\n\n"
    "Buyurtmani yuborasizmi?",
    reply_markup=kb
)


@dp.callback_query_handler(lambda c: c.data == "edit_order", state="*")
async def edit_order(call: types.CallbackQuery, state: FSMContext):

    await call.answer()

    await call.message.answer(
        "✏️ Buyurtmani qayta kiritish boshlandi.\n\n"
        "📐 ENINI kiriting (sm)"
    )

    await OrderState.width.set()

@dp.callback_query_handler(lambda c: c.data == "send_to_admin", state="*")
async def send_to_admin(call: types.CallbackQuery, state: FSMContext):

    data = await state.get_data()
    product = PRODUCTS[data["product_id"]]

    total_area = sum(s["area"] for s in data["sizes"])
    total_price = int(total_area * product["price"])

    sizes_text = ""

    for i, s in enumerate(data["sizes"], 1):
        sizes_text += f"{i}) {s['w']} x {s['h']} × {s['qty']} = {s['area']} m²\n"

    admin_text = (
        f"📥 YANGI BUYURTMA\n\n"
        f"🆔 Buyurtma: #{data['order_id']}\n"
        f"📦 Mahsulot: {product['name']}\n\n"
        f"📐 O‘lchamlar:\n{sizes_text}\n"
        f"📏 Umumiy: {total_area} m²\n"
        f"💰 Summa: {total_price:,} so‘m\n\n"
        f"📞 Telefon: {data['phone']}"
    )

    admin_kb = types.InlineKeyboardMarkup(row_width=2)

    admin_kb.add(
        types.InlineKeyboardButton(
            "✅ Qabul qilindi",
            callback_data=f"accept_{data['order_id']}"
        ),
        types.InlineKeyboardButton(
            "❌ Bekor qilindi",
            callback_data=f"cancel_{data['order_id']}"
        )
    )

    from config import ADMINS

    for admin_id in ADMINS:
        await call.message.bot.send_message(
            admin_id,
            admin_text,
            reply_markup=admin_kb
        )

    save_to_excel({
        "order_id": data["order_id"],
        "order_date": data["order_date"],
        "order_time": data["order_time"],
        "product_name": product["name"],
        "phone": data["phone"],
        "total_area": total_area,
        "total_price": total_price,
        "status": "Yangi"
    })

    ORDERS[data["order_id"]] = data

    await call.message.edit_text("✅ Buyurtma adminga yuborildi!")

    await state.finish()



    # 📤 ADMINLARGA YUBORISH
    from config import ADMINS
    for admin_id in ADMINS:
        await message.bot.send_message(admin_id, admin_text, reply_markup=admin_kb)

    # 📊 EXCELGA SAQLASH
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

    # 📦 ORDERS dictga saqlash
    ORDERS[data["order_id"]] = data

    # ✅ FOYDALANUVCHIGA JAVOB
    await message.answer(
    f"📦 Buyurtma yakuni:\n\n"
    f"📏 Umumiy maydon: {total_area} m²\n"
    f"💰 Jami summa: {total_price:,} so‘m\n\n"
    "✅ Buyurtmangiz qabul qilindi!\nTez orada bog‘lanamiz.",
    reply_markup=types.ReplyKeyboardRemove()
)
    await state.finish()


    

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

    ORDERS[data["order_id"]] = data 



    await state.finish()






# ================= CUTLIST (ADMIN) =================

@dp.callback_query_handler(lambda c: c.data.startswith("cutlist_"))
async def admin_cutlist(call: types.CallbackQuery):
    order_id = int(call.data.split("_")[1])

    data = ORDERS.get(order_id)
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
