"""Калькулятор пошива свадебных и вечерних платьев."""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.keyboards.inline import dress_base_kb, dress_options_kb
from bot.services.pricing import DressCalculator
from bot.states.order import CalcDress, Contacts
from bot.utils.texts import CALC_DRESS_SUMMARY


router = Router(name='dress_calc')


# ---------- ВХОД ----------

@router.callback_query(F.data.in_({'calc:wedding:start', 'calc:evening:start'}))
async def calc_start(call: CallbackQuery, state: FSMContext) -> None:
    is_wedding = call.data == 'calc:wedding:start'
    await state.set_state(CalcDress.choosing_base)
    await state.update_data(is_wedding=is_wedding, calc=None)

    title = '👰🏻‍♀️ <b>Свадебные платья</b>' if is_wedding else '🥂 <b>Вечерние платья</b>'
    await call.message.edit_text(
        f'{title}\n\nВыберите тип платья:',
        reply_markup=dress_base_kb(is_wedding),
    )
    await call.answer()


# ---------- ВЫБОР БАЗОВОГО ТИПА ----------

@router.callback_query(F.data.startswith('calc:wedding:base:') | F.data.startswith('calc:evening:base:'))
async def calc_base(call: CallbackQuery, state: FSMContext) -> None:
    parts = call.data.split(':')
    # parts = ['calc', 'wedding'|'evening', 'base', '<key>']
    is_wedding = parts[1] == 'wedding'
    base_type = parts[3]

    calc = DressCalculator(base_type=base_type, is_wedding=is_wedding)
    await state.update_data(calc=calc.to_dict())
    await state.set_state(CalcDress.choosing_options)

    await call.message.edit_text(
        CALC_DRESS_SUMMARY.format(summary=calc.summary(), total=calc.total()),
        reply_markup=dress_options_kb(is_wedding, calc.options, calc.is_urgent),
    )
    await call.answer()


# ---------- ОПЦИИ (toggle) ----------

@router.callback_query(F.data.startswith('calc:wedding:opt:') | F.data.startswith('calc:evening:opt:'))
async def calc_toggle_option(call: CallbackQuery, state: FSMContext) -> None:
    parts = call.data.split(':')
    is_wedding = parts[1] == 'wedding'
    opt_key = parts[3]

    data = await state.get_data()
    calc_data = data.get('calc')
    if not calc_data:
        await call.answer('Сессия истекла, начните заново.', show_alert=True)
        return

    calc = DressCalculator.from_dict(calc_data)
    calc.toggle_option(opt_key)
    await state.update_data(calc=calc.to_dict())

    await call.message.edit_text(
        CALC_DRESS_SUMMARY.format(summary=calc.summary(), total=calc.total()),
        reply_markup=dress_options_kb(is_wedding, calc.options, calc.is_urgent),
    )
    await call.answer()


# ---------- СРОЧНОСТЬ ----------

@router.callback_query(F.data.in_({'calc:wedding:urgent', 'calc:evening:urgent'}))
async def calc_toggle_urgent(call: CallbackQuery, state: FSMContext) -> None:
    is_wedding = 'wedding' in call.data
    data = await state.get_data()
    calc_data = data.get('calc')
    if not calc_data:
        await call.answer('Сессия истекла, начните заново.', show_alert=True)
        return

    calc = DressCalculator.from_dict(calc_data)
    calc.is_urgent = not calc.is_urgent
    await state.update_data(calc=calc.to_dict())

    await call.message.edit_text(
        CALC_DRESS_SUMMARY.format(summary=calc.summary(), total=calc.total()),
        reply_markup=dress_options_kb(is_wedding, calc.options, calc.is_urgent),
    )
    await call.answer()


# ---------- ОТПРАВКА ЗАЯВКИ ----------

@router.callback_query(F.data.in_({'calc:wedding:submit', 'calc:evening:submit'}))
async def calc_submit(call: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    calc_data = data.get('calc')
    if not calc_data:
        await call.answer('Сессия истекла, начните заново.', show_alert=True)
        return

    # переходим в сбор контактов; сохраняем тип заказа
    await state.update_data(
        order_type='wedding' if 'wedding' in call.data else 'evening',
        order_config=calc_data,
    )
    await state.set_state(Contacts.collecting)

    # вызываем хендлер контактов вручную
    from bot.handlers.contacts import show_contacts_screen
    await show_contacts_screen(call, state)
