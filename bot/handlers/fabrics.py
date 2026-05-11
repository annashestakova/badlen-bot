"""Просмотр каталога тканей по категориям. Данные – из БД (обновляются парсером decobay)."""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from bot.db.session import async_session_maker
from bot.db.models import Fabric, FabricCategory
from bot.keyboards.inline import fabrics_categories_kb, fabrics_list_kb
from bot.utils.texts import FABRICS_INTRO, FABRIC_CATEGORIES, FABRIC_CARD


router = Router(name='fabrics')


@router.callback_query(F.data == 'menu:fabrics')
async def cb_fabrics_categories(call: CallbackQuery) -> None:
    await call.message.edit_text(FABRICS_INTRO, reply_markup=fabrics_categories_kb())
    await call.answer()


@router.callback_query(F.data.startswith('fabric:cat:'))
async def cb_fabric_category(call: CallbackQuery) -> None:
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
            ).order_by(Fabric.name).limit(20)
        )
        fabrics = list(result.scalars().all())

    label = FABRIC_CATEGORIES.get(category_key, category_key)

    if not fabrics:
        b = InlineKeyboardBuilder()
        b.button(text='⬅️ К категориям', callback_data='menu:fabrics')
        b.button(text='🏠 В главное меню', callback_data='menu:main')
        b.adjust(1)
        await call.message.edit_text(
            f'{label}\n\n<i>Пока пусто. Загляните позже – мы постоянно пополняем каталог.</i>',
            reply_markup=b.as_markup(),
        )
        await call.answer()
        return

    await call.message.edit_text(
        f'{label}\n\nВыберите ткань – покажу фото и подробности:',
        reply_markup=fabrics_list_kb(fabrics, category_key),
    )
    await call.answer()


@router.callback_query(F.data.startswith('fabric:view:'))
async def cb_fabric_view(call: CallbackQuery) -> None:
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

    text = FABRIC_CARD.format(
        name=fabric.name,
        category=FABRIC_CATEGORIES.get(fabric.category.value, fabric.category.value),
        color=fabric.color or '—',
        description=fabric.description or '<i>Описание уточняется</i>',
        price=fabric.price_per_meter,
    )

    b = InlineKeyboardBuilder()
    b.button(text='🪡 Заказать корсет из этой ткани', callback_data='corset:constructor:start')
    b.button(text='⬅️ К категории', callback_data=f'fabric:cat:{fabric.category.value}')
    b.button(text='🏠 В главное меню', callback_data='menu:main')
    b.adjust(1)
    kb = b.as_markup()

    if fabric.image_url:
        try:
            await call.message.delete()
            await call.message.answer_photo(photo=fabric.image_url, caption=text, reply_markup=kb)
        except Exception:
            await call.message.answer(text, reply_markup=kb)
    else:
        await call.message.edit_text(text, reply_markup=kb)
    await call.answer()
