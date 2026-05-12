from typing import Optional
"""Inline-клавиатуры бота."""

from datetime import date as date_t, time as time_t

from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.config import settings
from bot.services.pricing import (
    WEDDING_BASE_LABELS, EVENING_BASE_LABELS, DRESS_OPTIONS,
    CORSET_TYPES, CORSET_CLOSURE, CORSET_OPTIONS,
)
from bot.utils.texts import FABRIC_CATEGORIES


# ---------- MAIN MENU ----------

def main_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text='👰🏻‍♀️ Свадебные платья', callback_data='menu:wedding')
    b.button(text='🥂 Вечерние платья', callback_data='menu:evening')
    b.button(text='🎀 Корсеты', callback_data='menu:corset')
    b.button(text='🪡 Ткани', callback_data='menu:fabrics')
    b.button(text='📅 Записаться на примерку', callback_data='menu:fitting')
    b.button(text='📚 Гайды', callback_data='menu:guides')
    b.button(text='🌿 О нас', callback_data='menu:about')
    b.adjust(1, 1, 1, 1, 1, 2)
    return b.as_markup()


def back_to_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text='⬅️ В главное меню', callback_data='menu:main')
    return b.as_markup()


# ---------- WEDDING / EVENING ----------

def wedding_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text='🎨 Калькулятор пошива', callback_data='calc:wedding:start')
    b.button(text='📚 Как подготовиться (невеста)', callback_data='guide:bride')
    b.button(text='📚 Подружке невесты', callback_data='guide:bridesmaid')
    b.button(text='📅 Записаться на примерку', callback_data='menu:fitting')
    b.button(text='⬅️ В главное меню', callback_data='menu:main')
    b.adjust(1)
    return b.as_markup()


def evening_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text='🎨 Калькулятор пошива', callback_data='calc:evening:start')
    b.button(text='📚 Как подготовиться', callback_data='guide:evening')
    b.button(text='📅 Записаться на примерку', callback_data='menu:fitting')
    b.button(text='⬅️ В главное меню', callback_data='menu:main')
    b.adjust(1)
    return b.as_markup()


# ---------- CORSET ----------

def corset_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text='✨ Образы с корсетом', callback_data='corset:looks')
    b.button(text='🪡 Конструктор корсета', callback_data='corset:constructor:start')
    b.button(text='📏 Снять мерки', callback_data='corset:measurements:start')
    b.button(text='📚 Как заказать корсет', callback_data='guide:corset_order')
    b.button(text='🪡 Выбрать ткань', callback_data='menu:fabrics')
    b.button(text='⬅️ В главное меню', callback_data='menu:main')
    b.adjust(1)
    return b.as_markup()


def corset_looks_kb(looks_keys: list[str]) -> InlineKeyboardMarkup:
    """looks_keys – ключи из texts.LOOK_DESCRIPTIONS."""
    b = InlineKeyboardBuilder()
    labels = {
        'casual_coffee': '☕ Casual coffee',
        'evening_champagne': '🥂 Evening champagne',
        'vintage_red': '🍷 Vintage red carpet',
        'bridal_red': '🌹 Bridal rebellion',
        'soft_denim': '👖 Soft denim',
        'peplum_office': '🤍 Peplum minimal',
        'pearl_bridal': '🤍 Pearl & ribbon bridal',
    }
    for key in looks_keys:
        b.button(text=labels.get(key, key), callback_data=f'look:show:{key}')
    b.button(text='🪡 К конструктору корсета', callback_data='corset:constructor:start')
    b.button(text='⬅️ В корсеты', callback_data='menu:corset')
    b.adjust(1)
    return b.as_markup()


def look_detail_kb(look_key: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text='🪡 Заказать корсет такого стиля', callback_data='corset:constructor:start')
    b.button(text='⬅️ К образам', callback_data='corset:looks')
    b.adjust(1)
    return b.as_markup()


# ---------- DRESS CALCULATOR ----------

def dress_base_kb(is_wedding: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    src = WEDDING_BASE_LABELS if is_wedding else EVENING_BASE_LABELS
    kind = 'wedding' if is_wedding else 'evening'
    for key, label in src.items():
        b.button(text=label, callback_data=f'calc:{kind}:base:{key}')
    b.button(text='⬅️ Назад', callback_data=f'menu:{kind}')
    b.adjust(1)
    return b.as_markup()


def dress_options_kb(is_wedding: bool, selected: list[str], is_urgent: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    kind = 'wedding' if is_wedding else 'evening'
    for key, opt in DRESS_OPTIONS.items():
        marker = '✅ ' if key in selected else '⬜ '
        b.button(
            text=f'{marker}{opt["label"]} (+{opt["price"]})',
            callback_data=f'calc:{kind}:opt:{key}',
        )
    urgent_marker = '✅ ' if is_urgent else '⬜ '
    b.button(text=f'{urgent_marker}⚡ Срочно (+30%)', callback_data=f'calc:{kind}:urgent')
    b.button(text='✨ Оформить заявку', callback_data=f'calc:{kind}:submit')
    b.button(text='⬅️ К выбору типа', callback_data=f'calc:{kind}:start')
    b.adjust(1)
    return b.as_markup()


# ---------- CORSET CONSTRUCTOR ----------

def corset_type_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for key, info in CORSET_TYPES.items():
        b.button(text=f'{info["label"]} – от {info["price"]} BYN', callback_data=f'corset:type:{key}')
    b.button(text='⬅️ К корсетам', callback_data='menu:corset')
    b.adjust(1)
    return b.as_markup()


def corset_fabric_categories_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for key, label in FABRIC_CATEGORIES.items():
        b.button(text=label, callback_data=f'corset:fabriccat:{key}')
    b.button(text='⬅️ Назад', callback_data='corset:constructor:back_to_type')
    b.adjust(2)
    return b.as_markup()


def corset_fabric_pick_kb(fabrics: list, category: str) -> InlineKeyboardMarkup:
    """fabrics – список объектов Fabric."""
    b = InlineKeyboardBuilder()
    for f in fabrics:
        b.button(
            text=f'{f.name} – {f.price_per_meter} BYN/м',
            callback_data=f'corset:fabric:{f.id}',
        )
    b.button(text='⬅️ К категориям', callback_data='corset:constructor:back_to_fabric_cat')
    b.adjust(1)
    return b.as_markup()


def corset_closure_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for key, info in CORSET_CLOSURE.items():
        b.button(text=f'{info["label"]} (+{info["price"]})', callback_data=f'corset:closure:{key}')
    b.button(text='⬅️ Назад', callback_data='corset:constructor:back_to_fabric_cat')
    b.adjust(1)
    return b.as_markup()


def corset_options_kb(selected: list[str], is_urgent: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for key, opt in CORSET_OPTIONS.items():
        marker = '✅ ' if key in selected else '⬜ '
        b.button(text=f'{marker}{opt["label"]} (+{opt["price"]})', callback_data=f'corset:opt:{key}')
    urgent_marker = '✅ ' if is_urgent else '⬜ '
    b.button(text=f'{urgent_marker}⚡ Срочно (+30%)', callback_data='corset:urgent')
    b.button(text='✨ Оформить заявку', callback_data='corset:submit')
    b.button(text='⬅️ К закрытию', callback_data='corset:constructor:back_to_closure')
    b.adjust(1)
    return b.as_markup()


# ---------- MEASUREMENTS ----------

def measurements_intro_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text='✅ Готова, начнём', callback_data='measure:start')
    b.button(text='⬅️ Назад', callback_data='menu:corset')
    b.adjust(1)
    return b.as_markup()


def measurement_step_kb(step: int, can_skip: bool = False) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if can_skip:
        b.button(text='⏭ Пропустить', callback_data=f'measure:skip:{step}')
    b.button(text='❌ Прервать', callback_data='menu:corset')
    b.adjust(1)
    return b.as_markup()


# ---------- FABRICS ----------

def fabrics_categories_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for key, label in FABRIC_CATEGORIES.items():
        b.button(text=label, callback_data=f'fabric:cat:{key}')
    b.button(text='⬅️ В главное меню', callback_data='menu:main')
    b.adjust(2)
    return b.as_markup()


def fabrics_list_kb(fabrics: list, category: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for f in fabrics:
        b.button(
            text=f'{f.name} – {f.price_per_meter} BYN/м',
            callback_data=f'fabric:view:{f.id}',
        )
    b.button(text='⬅️ К категориям', callback_data='menu:fabrics')
    b.adjust(1)
    return b.as_markup()


# ---------- CONTACTS / CONSENT ----------

def contacts_kb(has_phone: bool, has_email: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    phone_marker = '✅ ' if has_phone else ''
    email_marker = '✅ ' if has_email else ''
    b.button(text=f'{phone_marker}📞 Телефон', callback_data='contact:phone')
    b.button(text=f'{email_marker}📧 Email', callback_data='contact:email')
    if has_phone or has_email:
        b.button(text='➡️ Далее – согласие', callback_data='contact:next')
    b.adjust(1)
    return b.as_markup()


def share_phone_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text='📞 Поделиться номером', request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def consent_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text='✅ Согласна', callback_data='consent:yes')
    b.button(text='❌ Отмена', callback_data='menu:main')
    b.adjust(1)
    return b.as_markup()


# ---------- FITTING ----------

def fitting_dates_kb(slots_by_date: dict[date_t, list]) -> InlineKeyboardMarkup:
    """slots_by_date: {date: [FittingSlot, ...]}"""
    b = InlineKeyboardBuilder()
    for d in sorted(slots_by_date.keys()):
        count = len(slots_by_date[d])
        b.button(text=f'📅 {d.strftime("%d.%m")} ({count} слотов)', callback_data=f'fit:date:{d.isoformat()}')
    b.button(text='⬅️ В меню', callback_data='menu:main')
    b.adjust(2)
    return b.as_markup()


def fitting_times_kb(slots: list, date_iso: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for s in slots:
        b.button(text=f'⏰ {s.slot_time.strftime("%H:%M")}', callback_data=f'fit:slot:{s.id}')
    b.button(text='⬅️ К датам', callback_data='menu:fitting')
    b.adjust(3)
    return b.as_markup()


def fitting_after_request_kb(admin_username: Optional[str]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if admin_username:
        b.button(text='💬 Написать админу', url=f'https://t.me/{admin_username}')
    b.button(text='⬅️ В главное меню', callback_data='menu:main')
    b.adjust(1)
    return b.as_markup()


# ---------- ADMIN: подтверждение заявок/примерок ----------

def admin_order_kb(order_id: int, user_tg_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text='💬 Связаться с клиентом', url=f'tg://user?id={user_tg_id}')
    b.button(text='✅ В работу', callback_data=f'admin:order:accept:{order_id}')
    b.button(text='❌ Отменить', callback_data=f'admin:order:cancel:{order_id}')
    b.adjust(1, 2)
    return b.as_markup()


def admin_fitting_kb(fitting_id: int, user_tg_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text='💬 Связаться с клиентом', url=f'tg://user?id={user_tg_id}')
    b.button(text='✅ Подтвердить', callback_data=f'admin:fit:confirm:{fitting_id}')
    b.button(text='❌ Отклонить', callback_data=f'admin:fit:decline:{fitting_id}')
    b.adjust(1, 2)
    return b.as_markup()


# ---------- ADMIN PANEL ----------

def admin_panel_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text='📋 Открытые заявки', callback_data='admin:orders:list')
    b.button(text='📅 Примерки', callback_data='admin:fittings:list')
    b.button(text='➕ Добавить слот', callback_data='admin:slot:add')
    b.button(text='📸 Загрузить фото', callback_data='admin:photo:add')
    b.button(text='🪡 Обновить ткани', callback_data='admin:fabrics:refresh')
    b.button(text='⬅️ В главное меню', callback_data='menu:main')
    b.adjust(2, 2, 1, 1)
    return b.as_markup()
