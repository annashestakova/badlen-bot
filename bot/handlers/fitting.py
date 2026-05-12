from typing import Optional
"""Запись на примерку: клиент выбирает дату → время → админ подтверждает."""

from datetime import date as date_t, datetime, timedelta

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from bot.config import settings
from bot.db.session import async_session_maker
from bot.db.models import User, Order, OrderStatus, FittingSlot, Fitting, FittingStatus
from bot.keyboards.inline import (
    fitting_dates_kb, fitting_times_kb, fitting_after_request_kb,
    admin_fitting_kb, main_menu_kb,
)
from bot.states.order import Fitting as FittingFSM
from bot.utils.texts import (
    FITTING_INTRO, FITTING_PICK_TIME, FITTING_NO_SLOTS,
    FITTING_REQUESTED, FITTING_CONFIRMED, ADMIN_NEW_FITTING,
)


router = Router(name='fitting')


# ---------- ВЫБОР ДАТЫ ----------

@router.callback_query(F.data == 'menu:fitting')
async def cb_fitting_dates(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(FittingFSM.choosing_date)

    # ближайшие 30 дней
    today = date_t.today()
    horizon = today + timedelta(days=60)

    async with async_session_maker() as session:
        result = await session.execute(
            select(FittingSlot).where(
                FittingSlot.is_available == True,
                FittingSlot.slot_date >= today,
                FittingSlot.slot_date <= horizon,
            ).order_by(FittingSlot.slot_date, FittingSlot.slot_time)
        )
        slots = list(result.scalars().all())

    if not slots:
        await call.message.edit_text(FITTING_NO_SLOTS, reply_markup=main_menu_kb())
        await call.answer()
        return

    # группируем по дате
    by_date: dict[date_t, list] = {}
    for s in slots:
        by_date.setdefault(s.slot_date, []).append(s)

    await call.message.edit_text(FITTING_INTRO, reply_markup=fitting_dates_kb(by_date))
    await call.answer()


# ---------- ВЫБОР ВРЕМЕНИ ----------

@router.callback_query(F.data.startswith('fit:date:'))
async def cb_fitting_times(call: CallbackQuery, state: FSMContext) -> None:
    date_iso = call.data.split(':', 2)[-1]
    try:
        chosen_date = date_t.fromisoformat(date_iso)
    except ValueError:
        await call.answer('Неверная дата', show_alert=True)
        return

    async with async_session_maker() as session:
        result = await session.execute(
            select(FittingSlot).where(
                FittingSlot.slot_date == chosen_date,
                FittingSlot.is_available == True,
            ).order_by(FittingSlot.slot_time)
        )
        slots = list(result.scalars().all())

    if not slots:
        await call.answer('Слотов уже нет', show_alert=True)
        return

    await state.set_state(FittingFSM.choosing_time)
    await call.message.edit_text(
        FITTING_PICK_TIME.format(date=chosen_date.strftime('%d.%m.%Y')),
        reply_markup=fitting_times_kb(slots, date_iso),
    )
    await call.answer()


# ---------- БРОНИРОВАНИЕ СЛОТА ----------

@router.callback_query(F.data.startswith('fit:slot:'))
async def cb_fitting_book(call: CallbackQuery, state: FSMContext) -> None:
    try:
        slot_id = int(call.data.split(':')[-1])
    except ValueError:
        await call.answer('Ошибка', show_alert=True)
        return

    async with async_session_maker() as session:
        slot = await session.get(FittingSlot, slot_id)
        if not slot or not slot.is_available:
            await call.answer('Этот слот уже занят. Выберите другой.', show_alert=True)
            return

        # находим/создаём пользователя
        user_result = await session.execute(select(User).where(User.tg_id == call.from_user.id))
        user = user_result.scalar_one_or_none()
        if not user:
            user = User(tg_id=call.from_user.id, username=call.from_user.username, first_name=call.from_user.first_name)
            session.add(user)
            await session.flush()

        # ищем последний "висящий" заказ или создаём пустой
        last_order_result = await session.execute(
            select(Order).where(
                Order.user_id == user.id,
                Order.status.in_([OrderStatus.NEW, OrderStatus.AWAITING_FITTING]),
            ).order_by(Order.created_at.desc()).limit(1)
        )
        order = last_order_result.scalar_one_or_none()

        if not order:
            # клиент пришёл сразу на примерку без заказа — создаём заглушку
            from bot.db.models import ProductType
            order = Order(
                user_id=user.id,
                type=ProductType.WEDDING,  # дефолт; админ уточнит
                status=OrderStatus.AWAITING_FITTING,
                config={'note': 'Запись на примерку без оформленного заказа'},
                total_price=0,
            )
            session.add(order)
            await session.flush()

        # создаём заявку на примерку и блокируем слот
        fitting = Fitting(
            order_id=order.id,
            slot_id=slot.id,
            status=FittingStatus.REQUESTED,
        )
        session.add(fitting)
        slot.is_available = False  # сразу убираем из выдачи, чтобы не было гонок
        await session.commit()
        await session.refresh(fitting)

        date_str = slot.slot_date.strftime('%d.%m.%Y')
        time_str = slot.slot_time.strftime('%H:%M')

    # клиенту
    admin_username = None  # можно сохранить в Setting
    await call.message.edit_text(
        FITTING_REQUESTED.format(date=date_str, time=time_str),
        reply_markup=fitting_after_request_kb(admin_username),
    )
    await call.answer()
    await state.clear()

    # админам
    text = ADMIN_NEW_FITTING.format(
        order_id=order.id,
        name=call.from_user.first_name or '—',
        username=call.from_user.username or '—',
        phone=user.phone or '—',
        date=date_str,
        time=time_str,
    )
    kb = admin_fitting_kb(fitting.id, call.from_user.id)
    for admin_id in settings.admin_ids:
        try:
            await call.bot.send_message(admin_id, text, reply_markup=kb)
        except Exception:
            pass


# ---------- АДМИН: ПОДТВЕРЖДЕНИЕ / ОТКАЗ ----------

@router.callback_query(F.data.startswith('admin:fit:confirm:'))
async def admin_confirm(call: CallbackQuery) -> None:
    if call.from_user.id not in settings.admin_ids:
        await call.answer('Только для админа', show_alert=True)
        return

    fitting_id = int(call.data.split(':')[-1])

    async with async_session_maker() as session:
        fitting = await session.get(Fitting, fitting_id)
        if not fitting:
            await call.answer('Заявка не найдена', show_alert=True)
            return
        if fitting.status == FittingStatus.CONFIRMED:
            await call.answer('Уже подтверждена', show_alert=True)
            return

        fitting.status = FittingStatus.CONFIRMED
        slot = await session.get(FittingSlot, fitting.slot_id)
        # слот остаётся is_available=False
        order = await session.get(Order, fitting.order_id)
        user = await session.get(User, order.user_id)
        await session.commit()

        date_str = slot.slot_date.strftime('%d.%m.%Y')
        time_str = slot.slot_time.strftime('%H:%M')
        client_tg = user.tg_id

    # уведомление клиенту
    try:
        await call.bot.send_message(
            client_tg,
            FITTING_CONFIRMED.format(date=date_str, time=time_str),
        )
    except Exception:
        pass

    await call.message.edit_text(
        call.message.text + '\n\n✅ <b>Подтверждено</b>',
        reply_markup=None,
    )
    await call.answer('Подтверждено')


@router.callback_query(F.data.startswith('admin:fit:decline:'))
async def admin_decline(call: CallbackQuery) -> None:
    if call.from_user.id not in settings.admin_ids:
        await call.answer('Только для админа', show_alert=True)
        return

    fitting_id = int(call.data.split(':')[-1])

    async with async_session_maker() as session:
        fitting = await session.get(Fitting, fitting_id)
        if not fitting:
            await call.answer('Заявка не найдена', show_alert=True)
            return
        fitting.status = FittingStatus.DECLINED
        # возвращаем слот в выдачу
        slot = await session.get(FittingSlot, fitting.slot_id)
        slot.is_available = True
        order = await session.get(Order, fitting.order_id)
        user = await session.get(User, order.user_id)
        await session.commit()
        client_tg = user.tg_id

    try:
        await call.bot.send_message(
            client_tg,
            '🤍 К сожалению, выбранное время не подходит. Я свяжусь с вами для подбора другого варианта.',
        )
    except Exception:
        pass

    await call.message.edit_text(
        call.message.text + '\n\n❌ <b>Отклонено, слот возвращён в выдачу</b>',
        reply_markup=None,
    )
    await call.answer('Отклонено')
