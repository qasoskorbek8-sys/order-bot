# from aiogram.dispatcher.filters.state import State, StatesGroup

# class OrderState(StatesGroup):
#     waiting_for_count = State()     # nechta o‘lcham
#     waiting_for_width = State()     # eni
#     waiting_for_height = State()    # bo‘yi
#     waiting_for_name = State()      # 👈 YANGI
#     waiting_for_contact = State()   # keyin
#     waiting_for_quantity = State()  # 👈 YANGI



from aiogram.dispatcher.filters.state import State, StatesGroup

class OrderState(StatesGroup):

    width = State()
    height = State()
    qty = State()
    contact = State()

    product_name = State()
    product_price = State()
    product_photo = State()

    new_price = State()