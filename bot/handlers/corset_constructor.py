from typing import Optional
"""Конструктор корсета: тип → ткань → закрытие → опции → заказ."""

from decimal import Decimal

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from bot.db.session import async_session_maker
from bot.db.models import Fabric, FabricCategory
from bot.keyboards.inline import (
    corset_type_kb, corset_fabric_categories_kb, corset_fabric_pick_kb,
    corset_closure_kb, corset_options_kb,
)
from bot.services.pricing import CorsetCalculator, CORSET_TYPES, CORSET_CLOSURE
from bot.states.order import CalcCorset, Contacts
from bot.utils.texts import CORSET_CONSTRUCTOR_INTRO, CALC_CORSET_SUMMARY


router = Router(name='corset_constructor')


# ---------- ВХОД ----------

@router.callback_query(F.data == 'corset:constructor:start')
async def constructor_start(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(CalcCorset.choosing_type)
    calc = CorsetCalculator()
    await state.update_data(calc=calc.to_dict())
    await call.message.edit_text(
        CORSET_CONSTRUCTOR_INTRO + '\n\n<b>Шаг 1 из 5 — Тип корсета:</b>',
        reply_markup=corset_type_kb(),
    )
    await call.answer()


# ---------- 1) ТИП КОРСЕТА ----------

@router.callback_query(F.data.startswith('corset:type:'))
async def constructor_pick_type(call: CallbackQuery, state: FSMContext) -> None:
    corset_type = call.data.split(':')[-1]
    if corset_type not in CORSET_TYPES:
        await call.answer('Неизвестный тип корсета', show_alert=True)
        return

    data = await state.get_data()
    calc = CorsetCalculator.from_dict(data.get('calc', {}))
    calc.corset_type = corset_type
    await state.update_data(calc=calc.to_dict())
    await state.set_state(CalcCorset.choosing_fabric_category)

    info = CORSET_TYPES[corset_type]
    text = (
        f'{info["label"]}\n<i>{info["description"]}</i>\n\n'
        f'<b>Текущая сборка:</b>\n{calc.summary()}\n\n'
        f'💰 <b>Сейчас: {calc.total()} BYN</b>\n\n'
        '<b>Шаг 2 из 5 — Выберите категорию ткани:</b>'
    )
    await call.message.edit_text(text, reply_markup=corset_fabric_categories_kb())
    await call.answer()


# ---------- НАЗАД к типу ----------

@router.callback_query(F.data == 'corset:constructor:back_to_type')
async def back_to_type(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(CalcCorset.choosing_type)
    await call.message.edit_text(
        CORSET_CONSTRUCTOR_INTRO + '\n\n<b>Шаг 1 из 5 — Тип корсета:</b>',
        reply_markup=corset_type_kb(),
    )
    await call.answer()


# ---------- 2) КАТЕГОРИЯ ТКАНИ ----------

@router.callback_query(F.data.startswith('corset:fabriccat:'))
async def constructor_pick_fabric_cat(call: CallbackQuery, state: FSMContext) -> None:
    category_key = call.data.split(':')[-1]
    try:
        category = FabricCategory(category_key)
    except ValueError:
        await call.answer('Неизвестная категория', show_alert=True)
        return

    async with async_session_maker() as session:
        result = await session.execute(
            select(Fabric).where(
                Fabric.category == category,
                Fabric.is_available == True,
            ).limit(20)
        )
        fabrics = list(result.scalars().all())

    if not fabrics:
        await call.answer('В этой категории пока пусто. Выберите другую.', show_alert=True)
        return

    await state.update_data(fabric_category=category_key)
    await state.set_state(CalcCorset.choosing_fabric)
    await call.message.edit_text(
        f'🪡 <b>Выберите ткань:</b>',
        reply_markup=corset_fabric_pick_kb(fabrics, category_key),
    )
    await call.answer()


# ---------- НАЗАД к категории ткани ----------

@router.callback_query(F.data == 'corset:constructor:back_to_fabric_cat')
async def back_to_fabric_cat(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(CalcCorset.choosing_fabric_category)
    await call.message.edit_text(
        '🪡 <b>Шаг 2 из 5 — Выберите категорию ткани:</b>',
        reply_markup=corset_fabric_categories_kb(),
    )
    await call.answer()


# ---------- 3) ТКАНЬ ----------

@router.callback_query(F.data.startswith('corset:fabric:'))
async def constructor_pick_fabric(call: CallbackQuery, state: FSMContext) -> None:
    try:
        fabric_id = int(call.data.split(':')[-1])
    except ValueError:
        await call.answer('Ошибка', show_alert=True)
        return

    async with async_session_maker() as session:
        fabric = await session.get(Fabric, fabric_id)

    if not fabric:
        await call.answer('Ткань не найдена', show_alert=True)
        return

    data = await state.get_data()
    calc = CorsetCalculator.from_dict(data.get('calc', {}))
    calc.fabric_id = fabric.id
    calc.fabric_name = fabric.name
    calc.fabric_price_per_m = Decimal(fabric.price_per_meter)
    await state.update_data(calc=calc.to_dict())
    await state.set_state(CalcCorset.choosing_closure)

    text = (
        f'✅ Ткань: <b>{fabric.name}</b>\n\n'
        f'<b>Текущая сборка:</b>\n{calc.summary()}\n\n'
        f'💰 <b>Сейчас: {calc.total()} BYN</b>\n\n'
        '<b>Шаг 3 из 5 — Как будет закрываться корсет?</b>'
    )
    await call.message.edit_text(text, reply_markup=corset_closure_kb())
    await call.answer()


# ---------- 4) ЗАКРЫТИЕ ----------

@router.callback_query(F.data.startswith('corset:closure:'))
async def constructor_pick_closure(call: CallbackQuery, state: FSMContext) -> None:
    closure_key = call.data.split(':')[-1]
    if closure_key not in CORSET_CLOSURE:
        await call.answer('Неизвестный вариант', show_alert=True)
        return

    data = await state.get_data()
    calc = CorsetCalculator.from_dict(data.get('calc', {}))
    calc.closure = closure_key
    await state.update_data(calc=calc.to_dict())
    await state.set_state(CalcCorset.choosing_options)

    text = (
        f'✅ Закрытие: <b>{CORSET_CLOSURE[closure_key]["label"]}</b>\n\n'
        f'<b>Текущая сборка:</b>\n{calc.summary()}\n\n'
        f'💰 <b>Сейчас: {calc.total()} BYN</b>\n\n'
        '<b>Шаг 4 из 5 — Дополнительные опции:</b>'
    )
    await call.message.edit_text(
        text,
        reply_markup=corset_options_kb(calc.options, calc.is_urgent),
    )
    await call.answer()


# ---------- НАЗАД к закрытию ----------

@router.callback_query(F.data == 'corset:constructor:back_to_closure')
async def back_to_closure(call: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    calc = CorsetCalculator.from_dict(data.get('calc', {}))
    await state.set_state(CalcCorset.choosing_closure)
    await call.message.edit_text(
        f'<b>Текущая сборка:</b>\n{calc.summary()}\n\n'
        f'💰 <b>Сейчас: {calc.total()} BYN</b>\n\n'
        '<b>Шаг 3 из 5 — Как будет закрываться корсет?</b>',
        reply_markup=corset_closure_kb(),
    )
    await call.answer()


# ---------- ОПЦИИ (toggle) ----------

@router.callback_query(F.data.startswith('corset:opt:'))
async def constructor_toggle_option(call: CallbackQuery, state: FSMContext) -> None:
    opt_key = call.data.split(':')[-1]
    data = await state.get_data()
    calc = CorsetCalculator.from_dict(data.get('calc', {}))
    if opt_key in calc.options:
        calc.options.remove(opt_key)
    else:
        calc.options.append(opt_key)
    await state.update_data(calc=calc.to_dict())

    await call.message.edit_text(
        CALC_CORSET_SUMMARY.format(summary=calc.summary(), total=calc.total()),
        reply_markup=corset_options_kb(calc.options, calc.is_urgent),
    )
    await call.answer()


# ---------- СРОЧНОСТЬ ----------

@router.callback_query(F.data == 'corset:urgent')
async def constructor_toggle_urgent(call: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    calc = CorsetCalculator.from_dict(data.get('calc', {}))
    calc.is_urgent = not calc.is_urgent
    await state.update_data(calc=calc.to_dict())

    await call.message.edit_text(
        CALC_CORSET_SUMMARY.format(summary=calc.summary(), total=calc.total()),
        reply_markup=corset_options_kb(calc.options, calc.is_urgent),
    )
    await call.answer()


# ---------- ОТПРАВКА ЗАЯВКИ ----------

@router.callback_query(F.data == 'corset:submit')
async def constructor_submit(call: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    calc_data = data.get('calc')
    if not calc_data:
        await call.answer('Сессия истекла, начните заново.', show_alert=True)
        return

    calc = CorsetCalculator.from_dict(calc_data)
    if not calc.corset_type or not calc.fabric_id or not calc.closure:
        await call.answer('Заполните все шаги конструктора.', show_alert=True)
        return

    await state.update_data(
        order_type='corset',
        order_config=calc_data,
    )
    await state.set_state(Contacts.collecting)

    from bot.handlers.contacts import show_contacts_screen
    await show_contacts_screen(call, state)
