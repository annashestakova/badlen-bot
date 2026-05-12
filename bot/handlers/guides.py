from typing import Optional
"""Гайды по подготовке к примеркам и заказу корсета."""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.utils.texts import (
    GUIDE_BRIDE, GUIDE_BRIDESMAID, GUIDE_EVENING, GUIDE_CORSET_ORDER,
)


router = Router(name='guides')


def _back_kb(back_to: str):
    b = InlineKeyboardBuilder()
    b.button(text='⬅️ Назад', callback_data=back_to)
    b.button(text='🏠 В главное меню', callback_data='menu:main')
    b.adjust(1)
    return b.as_markup()


@router.callback_query(F.data == 'menu:guides')
async def cb_guides_menu(call: CallbackQuery) -> None:
    b = InlineKeyboardBuilder()
    b.button(text='👰🏻‍♀️ Подготовка – невеста', callback_data='guide:bride')
    b.button(text='🌷 Подготовка – подружка невесты', callback_data='guide:bridesmaid')
    b.button(text='🥂 Подготовка – вечернее платье', callback_data='guide:evening')
    b.button(text='🎀 Как заказать корсет', callback_data='guide:corset_order')
    b.button(text='⬅️ В главное меню', callback_data='menu:main')
    b.adjust(1)
    await call.message.edit_text('📚 <b>Гайды</b>\n\nВыберите, что почитать:', reply_markup=b.as_markup())
    await call.answer()


@router.callback_query(F.data == 'guide:bride')
async def cb_guide_bride(call: CallbackQuery) -> None:
    await call.message.edit_text(GUIDE_BRIDE, reply_markup=_back_kb('menu:guides'))
    await call.answer()


@router.callback_query(F.data == 'guide:bridesmaid')
async def cb_guide_bridesmaid(call: CallbackQuery) -> None:
    await call.message.edit_text(GUIDE_BRIDESMAID, reply_markup=_back_kb('menu:guides'))
    await call.answer()


@router.callback_query(F.data == 'guide:evening')
async def cb_guide_evening(call: CallbackQuery) -> None:
    await call.message.edit_text(GUIDE_EVENING, reply_markup=_back_kb('menu:guides'))
    await call.answer()


@router.callback_query(F.data == 'guide:corset_order')
async def cb_guide_corset(call: CallbackQuery) -> None:
    b = InlineKeyboardBuilder()
    b.button(text='🪡 Начать заказ корсета', callback_data='corset:constructor:start')
    b.button(text='⬅️ К гайдам', callback_data='menu:guides')
    b.button(text='🏠 В главное меню', callback_data='menu:main')
    b.adjust(1)
    await call.message.edit_text(GUIDE_CORSET_ORDER, reply_markup=b.as_markup())
    await call.answer()
