from typing import Optional
"""/start и навигация по главному меню."""

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from bot.db.session import async_session_maker
from bot.db.models import User
from bot.keyboards.inline import main_menu_kb, back_to_menu_kb, wedding_menu_kb, evening_menu_kb, corset_menu_kb
from bot.utils.texts import (
    WELCOME, ABOUT, MENU_PROMPT,
    WEDDING_INTRO, EVENING_INTRO, CORSET_INTRO,
)


router = Router(name='start')


async def ensure_user(tg_user) -> User:
    """Гарантирует наличие пользователя в БД, возвращает запись."""
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_user.id))
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                tg_id=tg_user.id,
                username=tg_user.username,
                first_name=tg_user.first_name,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        else:
            # обновим имя/юзернейм если поменялись
            changed = False
            if user.username != tg_user.username:
                user.username = tg_user.username
                changed = True
            if user.first_name != tg_user.first_name:
                user.first_name = tg_user.first_name
                changed = True
            if changed:
                await session.commit()
        return user


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await ensure_user(message.from_user)
    await message.answer(WELCOME, reply_markup=main_menu_kb())


@router.message(Command('menu'))
async def cmd_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(MENU_PROMPT, reply_markup=main_menu_kb())


@router.callback_query(F.data == 'menu:main')
async def cb_main_menu(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_text(WELCOME, reply_markup=main_menu_kb())
    await call.answer()


@router.callback_query(F.data == 'menu:about')
async def cb_about(call: CallbackQuery) -> None:
    await call.message.edit_text(ABOUT, reply_markup=back_to_menu_kb())
    await call.answer()


@router.callback_query(F.data == 'menu:wedding')
async def cb_wedding(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_text(WEDDING_INTRO, reply_markup=wedding_menu_kb())
    await call.answer()


@router.callback_query(F.data == 'menu:evening')
async def cb_evening(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_text(EVENING_INTRO, reply_markup=evening_menu_kb())
    await call.answer()


@router.callback_query(F.data == 'menu:corset')
async def cb_corset(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_text(CORSET_INTRO, reply_markup=corset_menu_kb())
    await call.answer()
