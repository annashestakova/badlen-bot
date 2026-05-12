from typing import Optional
"""Пошаговое снятие мерок для корсета. 8 обязательных шагов + 9-й (заметки)."""

from decimal import Decimal

from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from bot.db.session import async_session_maker
from bot.db.models import User, CorsetMeasurement
from bot.keyboards.inline import (
    measurements_intro_kb, measurement_step_kb, corset_menu_kb,
)
from bot.states.order import Measurements
from bot.utils.texts import (
    MEASUREMENTS_INTRO, MEASUREMENTS_STEPS, MEASUREMENT_INVALID, MEASUREMENTS_DONE,
)
from bot.utils.validators import safe_float, sanitize_text


router = Router(name='measurements')


# ---------- ВХОД ----------

@router.callback_query(F.data == 'corset:measurements:start')
async def measurements_intro(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.update_data(m={})
    await call.message.edit_text(MEASUREMENTS_INTRO, reply_markup=measurements_intro_kb())
    await call.answer()


@router.callback_query(F.data == 'measure:start')
async def measurements_step_1(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(Measurements.step_1_bust)
    await call.message.edit_text(
        MEASUREMENTS_STEPS[1],
        reply_markup=measurement_step_kb(1, can_skip=False),
    )
    await call.answer()


# ---------- ШАГ 1: обхват груди ----------

@router.message(StateFilter(Measurements.step_1_bust), F.text)
async def step_1(message: Message, state: FSMContext) -> None:
    value = safe_float(message.text)
    if value is None:
        await message.answer(MEASUREMENT_INVALID)
        return
    data = await state.get_data()
    m = data.get('m', {})
    m['bust'] = value
    await state.update_data(m=m)
    await state.set_state(Measurements.step_2_bra_size)
    await message.answer(MEASUREMENTS_STEPS[2], reply_markup=measurement_step_kb(2))


# ---------- ШАГ 2: размер бюстгальтера ----------

@router.message(StateFilter(Measurements.step_2_bra_size), F.text)
async def step_2(message: Message, state: FSMContext) -> None:
    raw = sanitize_text(message.text, max_len=16)
    if len(raw) < 2 or len(raw) > 16:
        await message.answer('❌ Введите размер, например: <code>75C</code>')
        return
    data = await state.get_data()
    m = data.get('m', {})
    m['bra_size'] = raw
    await state.update_data(m=m)
    await state.set_state(Measurements.step_3_under_bust)
    await message.answer(MEASUREMENTS_STEPS[3], reply_markup=measurement_step_kb(3))


# ---------- ШАГ 3: под грудью ----------

@router.message(StateFilter(Measurements.step_3_under_bust), F.text)
async def step_3(message: Message, state: FSMContext) -> None:
    value = safe_float(message.text)
    if value is None:
        await message.answer(MEASUREMENT_INVALID)
        return
    data = await state.get_data()
    m = data.get('m', {})
    m['under_bust'] = value
    await state.update_data(m=m)
    await state.set_state(Measurements.step_4_waist)
    await message.answer(MEASUREMENTS_STEPS[4], reply_markup=measurement_step_kb(4))


# ---------- ШАГ 4: талия ----------

@router.message(StateFilter(Measurements.step_4_waist), F.text)
async def step_4(message: Message, state: FSMContext) -> None:
    value = safe_float(message.text)
    if value is None:
        await message.answer(MEASUREMENT_INVALID)
        return
    data = await state.get_data()
    m = data.get('m', {})
    m['waist'] = value
    await state.update_data(m=m)
    await state.set_state(Measurements.step_5_desired_tight)
    await message.answer(MEASUREMENTS_STEPS[5], reply_markup=measurement_step_kb(5))


# ---------- ШАГ 5: утяжка ----------

@router.message(StateFilter(Measurements.step_5_desired_tight), F.text)
async def step_5(message: Message, state: FSMContext) -> None:
    value = safe_float(message.text)
    if value is None or value > 20:
        await message.answer('❌ Введите утяжку в см (обычно 5–15). Например: <code>7</code>')
        return
    data = await state.get_data()
    m = data.get('m', {})
    m['desired_tight'] = value
    await state.update_data(m=m)
    await state.set_state(Measurements.step_6_belly)
    await message.answer(MEASUREMENTS_STEPS[6], reply_markup=measurement_step_kb(6, can_skip=True))


# ---------- ШАГ 6: живот (опционально) ----------

@router.message(StateFilter(Measurements.step_6_belly), F.text)
async def step_6(message: Message, state: FSMContext) -> None:
    value = safe_float(message.text)
    if value is None:
        await message.answer(MEASUREMENT_INVALID)
        return
    data = await state.get_data()
    m = data.get('m', {})
    m['belly'] = value
    await state.update_data(m=m)
    await state.set_state(Measurements.step_7_hips)
    await message.answer(MEASUREMENTS_STEPS[7], reply_markup=measurement_step_kb(7))


@router.callback_query(F.data == 'measure:skip:6')
async def skip_6(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(Measurements.step_7_hips)
    await call.message.edit_text(MEASUREMENTS_STEPS[7], reply_markup=measurement_step_kb(7))
    await call.answer()


# ---------- ШАГ 7: бёдра ----------

@router.message(StateFilter(Measurements.step_7_hips), F.text)
async def step_7(message: Message, state: FSMContext) -> None:
    value = safe_float(message.text)
    if value is None:
        await message.answer(MEASUREMENT_INVALID)
        return
    data = await state.get_data()
    m = data.get('m', {})
    m['hips'] = value
    await state.update_data(m=m)
    await state.set_state(Measurements.step_8_waist_to_under_bust)
    await message.answer(MEASUREMENTS_STEPS[8], reply_markup=measurement_step_kb(8))


# ---------- ШАГ 8: талия→под грудью ----------

@router.message(StateFilter(Measurements.step_8_waist_to_under_bust), F.text)
async def step_8(message: Message, state: FSMContext) -> None:
    value = safe_float(message.text)
    if value is None:
        await message.answer(MEASUREMENT_INVALID)
        return
    data = await state.get_data()
    m = data.get('m', {})
    m['waist_to_under_bust'] = value
    await state.update_data(m=m)
    await state.set_state(Measurements.step_9_figure_notes)
    await message.answer(MEASUREMENTS_STEPS[9], reply_markup=measurement_step_kb(9, can_skip=True))


# ---------- ШАГ 9: заметки (опционально) ----------

@router.message(StateFilter(Measurements.step_9_figure_notes), F.text)
async def step_9(message: Message, state: FSMContext) -> None:
    notes = sanitize_text(message.text, max_len=1000)
    data = await state.get_data()
    m = data.get('m', {})
    m['figure_notes'] = notes
    await _save_measurements(message.from_user.id, m)
    await state.clear()
    await message.answer(MEASUREMENTS_DONE, reply_markup=corset_menu_kb())


@router.callback_query(F.data == 'measure:skip:9')
async def skip_9(call: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    m = data.get('m', {})
    await _save_measurements(call.from_user.id, m)
    await state.clear()
    await call.message.edit_text(MEASUREMENTS_DONE, reply_markup=corset_menu_kb())
    await call.answer()


# ---------- SAVE ----------

async def _save_measurements(tg_id: int, m: dict) -> None:
    async with async_session_maker() as session:
        user_result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = user_result.scalar_one_or_none()
        if not user:
            return

        meas = CorsetMeasurement(
            user_id=user.id,
            bust=Decimal(str(m['bust'])) if 'bust' in m else None,
            bra_size=m.get('bra_size'),
            under_bust=Decimal(str(m['under_bust'])) if 'under_bust' in m else None,
            waist=Decimal(str(m['waist'])) if 'waist' in m else None,
            desired_tight=Decimal(str(m['desired_tight'])) if 'desired_tight' in m else None,
            belly=Decimal(str(m['belly'])) if 'belly' in m else None,
            hips=Decimal(str(m['hips'])) if 'hips' in m else None,
            waist_to_under_bust=Decimal(str(m['waist_to_under_bust'])) if 'waist_to_under_bust' in m else None,
            figure_notes=m.get('figure_notes'),
        )
        session.add(meas)
        await session.commit()
