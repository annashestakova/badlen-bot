from typing import Optional
"""Сбор контактов: телефон + email (хотя бы один) + имя + согласие.
После согласия сохраняем заказ и отправляем админу."""

import json

from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from bot.config import settings
from bot.db.session import async_session_maker
from bot.db.models import User, Order, ProductType, OrderStatus
from bot.keyboards.inline import (
    contacts_kb, share_phone_kb, consent_kb, admin_order_kb, main_menu_kb,
)
from bot.states.order import Contacts, Delivery
from bot.utils.texts import (
    CONTACTS_REQUEST, PHONE_REQUEST, PHONE_INVALID,
    EMAIL_REQUEST, EMAIL_INVALID, NAME_REQUEST,
    CONSENT_TEXT, CONSENT_REQUIRED, DELIVERY_REQUEST,
    ORDER_CREATED, ADMIN_NEW_ORDER,
)
from bot.utils.validators import normalize_phone_by, validate_email, sanitize_text
from bot.services.pricing import (
    DressCalculator, CorsetCalculator,
    WEDDING_BASE_LABELS, EVENING_BASE_LABELS, DRESS_OPTIONS,
    CORSET_TYPES, CORSET_CLOSURE, CORSET_OPTIONS,
)


router = Router(name='contacts')


# ---------- ПОКАЗ ЭКРАНА КОНТАКТОВ ----------

async def show_contacts_screen(call_or_msg, state: FSMContext) -> None:
    """Универсально для CallbackQuery и Message."""
    data = await state.get_data()
    has_phone = bool(data.get('contact_phone'))
    has_email = bool(data.get('contact_email'))
    text = CONTACTS_REQUEST
    if has_phone:
        text += f'\n\n✅ Телефон: <code>{data["contact_phone"]}</code>'
    if has_email:
        text += f'\n✅ Email: <code>{data["contact_email"]}</code>'

    kb = contacts_kb(has_phone, has_email)

    if isinstance(call_or_msg, CallbackQuery):
        try:
            await call_or_msg.message.edit_text(text, reply_markup=kb)
        except Exception:
            await call_or_msg.message.answer(text, reply_markup=kb)
        await call_or_msg.answer()
    else:
        await call_or_msg.answer(text, reply_markup=kb)


# ---------- ВЫБОР: ВВЕСТИ ТЕЛЕФОН ----------

@router.callback_query(F.data == 'contact:phone', StateFilter(Contacts.collecting))
async def cb_contact_phone(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(Contacts.waiting_phone)
    await call.message.answer(PHONE_REQUEST, reply_markup=share_phone_kb())
    await call.answer()


@router.message(StateFilter(Contacts.waiting_phone), F.contact)
async def msg_phone_via_contact(message: Message, state: FSMContext) -> None:
    raw = message.contact.phone_number
    if not raw.startswith('+'):
        raw = '+' + raw
    normalized = normalize_phone_by(raw)
    if not normalized:
        await message.answer(PHONE_INVALID)
        return
    await state.update_data(contact_phone=normalized)
    await message.answer('✅ Телефон сохранён', reply_markup=ReplyKeyboardRemove())
    await state.set_state(Contacts.collecting)
    await show_contacts_screen(message, state)


@router.message(StateFilter(Contacts.waiting_phone), F.text)
async def msg_phone_text(message: Message, state: FSMContext) -> None:
    normalized = normalize_phone_by(message.text)
    if not normalized:
        await message.answer(PHONE_INVALID)
        return
    await state.update_data(contact_phone=normalized)
    await message.answer('✅ Телефон сохранён', reply_markup=ReplyKeyboardRemove())
    await state.set_state(Contacts.collecting)
    await show_contacts_screen(message, state)


# ---------- ВЫБОР: ВВЕСТИ EMAIL ----------

@router.callback_query(F.data == 'contact:email', StateFilter(Contacts.collecting))
async def cb_contact_email(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(Contacts.waiting_email)
    await call.message.answer(EMAIL_REQUEST)
    await call.answer()


@router.message(StateFilter(Contacts.waiting_email), F.text)
async def msg_email(message: Message, state: FSMContext) -> None:
    normalized = validate_email(message.text)
    if not normalized:
        await message.answer(EMAIL_INVALID)
        return
    await state.update_data(contact_email=normalized)
    await message.answer('✅ Email сохранён')
    await state.set_state(Contacts.collecting)
    await show_contacts_screen(message, state)


# ---------- ДАЛЕЕ → ИМЯ → СОГЛАСИЕ ----------

@router.callback_query(F.data == 'contact:next', StateFilter(Contacts.collecting))
async def cb_contact_next(call: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    if not data.get('contact_phone') and not data.get('contact_email'):
        await call.answer('Нужен хотя бы один контакт.', show_alert=True)
        return
    await state.set_state(Contacts.waiting_name)
    await call.message.answer(NAME_REQUEST)
    await call.answer()


@router.message(StateFilter(Contacts.waiting_name), F.text)
async def msg_name(message: Message, state: FSMContext) -> None:
    name = sanitize_text(message.text, max_len=64)
    if len(name) < 2:
        await message.answer('❌ Имя слишком короткое.')
        return
    await state.update_data(contact_name=name)

    # для корсета - сначала адрес доставки
    data = await state.get_data()
    if data.get('order_type') == 'corset':
        await state.set_state(Delivery.waiting_address)
        await message.answer(DELIVERY_REQUEST)
    else:
        await state.set_state(Contacts.waiting_consent)
        await message.answer(CONSENT_TEXT, reply_markup=consent_kb())


@router.message(StateFilter(Delivery.waiting_address), F.text)
async def msg_address(message: Message, state: FSMContext) -> None:
    addr = sanitize_text(message.text, max_len=500)
    if len(addr) < 10:
        await message.answer('❌ Адрес слишком короткий. Укажите город, улицу, дом, квартиру, индекс.')
        return
    await state.update_data(delivery_address=addr)
    await state.set_state(Contacts.waiting_consent)
    await message.answer(CONSENT_TEXT, reply_markup=consent_kb())


# ---------- СОГЛАСИЕ → СОЗДАНИЕ ЗАКАЗА ----------

@router.callback_query(F.data == 'consent:yes', StateFilter(Contacts.waiting_consent))
async def cb_consent(call: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    order_type = data.get('order_type')
    order_config = data.get('order_config') or {}

    if not order_type:
        await call.answer('Сессия истекла, начните заново.', show_alert=True)
        return

    # сохраняем заказ
    async with async_session_maker() as session:
        user_result = await session.execute(select(User).where(User.tg_id == call.from_user.id))
        user = user_result.scalar_one_or_none()
        if not user:
            user = User(tg_id=call.from_user.id, username=call.from_user.username, first_name=call.from_user.first_name)
            session.add(user)
            await session.flush()

        # обновляем профиль контактов
        if data.get('contact_phone'):
            user.phone = data['contact_phone']
        if data.get('contact_email'):
            user.email = data['contact_email']
        user.consent_personal_data = True

        # конвертируем тип
        ptype_map = {'wedding': ProductType.WEDDING, 'evening': ProductType.EVENING, 'corset': ProductType.CORSET}
        ptype = ptype_map[order_type]

        total = order_config.get('total', '0')
        from decimal import Decimal as D
        order = Order(
            user_id=user.id,
            type=ptype,
            status=OrderStatus.NEW,
            config=order_config,
            total_price=D(total),
            contact_phone=data.get('contact_phone'),
            contact_email=data.get('contact_email'),
            contact_name=data.get('contact_name'),
            delivery_address=data.get('delivery_address'),
            is_urgent=order_config.get('is_urgent', False),
        )
        session.add(order)
        await session.commit()
        await session.refresh(order)
        order_id = order.id

    # уведомление клиенту
    await call.message.edit_text(
        ORDER_CREATED.format(order_id=order_id),
        reply_markup=main_menu_kb(),
    )
    await call.answer()
    await state.clear()

    # уведомление админу(ам)
    await _notify_admins(call.bot, order_id, order_type, order_config, data, call.from_user)


@router.callback_query(F.data == 'consent:no', StateFilter(Contacts.waiting_consent))
async def cb_consent_no(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer(CONSENT_REQUIRED, show_alert=True)


# ---------- АДМИН-УВЕДОМЛЕНИЕ ----------

async def _notify_admins(bot, order_id, order_type, order_config, data, tg_user) -> None:
    """Расшифровывает конфиг заказа в человекочитаемый текст и отправляет всем админам."""
    if order_type in ('wedding', 'evening'):
        calc = DressCalculator.from_dict(order_config)
        config_text = calc.summary()
        type_label = '👰🏻‍♀️ Свадебное' if order_type == 'wedding' else '🥂 Вечернее'
    elif order_type == 'corset':
        calc = CorsetCalculator.from_dict(order_config)
        config_text = calc.summary()
        type_label = '🎀 Корсет'
    else:
        config_text = json.dumps(order_config, ensure_ascii=False, indent=2, default=str)
        type_label = order_type

    text = ADMIN_NEW_ORDER.format(
        order_id=order_id,
        type=type_label,
        name=data.get('contact_name', '—'),
        username=tg_user.username or '—',
        tg_id=tg_user.id,
        phone=data.get('contact_phone', '—'),
        email=data.get('contact_email', '—'),
        address=data.get('delivery_address', '—'),
        config=config_text,
        total=order_config.get('total', '0'),
    )
    kb = admin_order_kb(order_id, tg_user.id)

    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(admin_id, text, reply_markup=kb)
        except Exception:
            pass
