"""FSM states для многошаговых диалогов."""

from aiogram.fsm.state import State, StatesGroup


class CalcDress(StatesGroup):
    """Калькулятор платьев (свадебных и вечерних)."""
    choosing_base = State()
    choosing_options = State()


class CalcCorset(StatesGroup):
    """Конструктор корсета."""
    choosing_type = State()
    choosing_fabric_category = State()
    choosing_fabric = State()
    choosing_closure = State()
    choosing_options = State()


class Contacts(StatesGroup):
    """Сбор контактов."""
    collecting = State()
    waiting_phone = State()
    waiting_email = State()
    waiting_name = State()
    waiting_consent = State()


class Delivery(StatesGroup):
    """Адрес доставки (для корсетов)."""
    waiting_address = State()


class Fitting(StatesGroup):
    """Запись на примерку."""
    choosing_date = State()
    choosing_time = State()


class Measurements(StatesGroup):
    """Снятие мерок корсета — 8 шагов."""
    step_1_bust = State()
    step_2_bra_size = State()
    step_3_under_bust = State()
    step_4_waist = State()
    step_5_desired_tight = State()
    step_6_belly = State()
    step_7_hips = State()
    step_8_waist_to_under_bust = State()
    step_9_figure_notes = State()


class AdminAddSlot(StatesGroup):
    """Админ добавляет слот для примерки."""
    waiting_date = State()
    waiting_time = State()


class AdminAddProduct(StatesGroup):
    """Админ загружает фото в галерею."""
    waiting_type = State()
    waiting_title = State()
    waiting_description = State()
    waiting_price = State()
    waiting_look = State()
    waiting_photo = State()
