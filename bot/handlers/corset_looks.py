from typing import Optional
"""Образы с корсетом — галерея луков из БД (загружается админом)."""

from aiogram import Router, F
from aiogram.types import CallbackQuery, InputMediaPhoto
from sqlalchemy import select

from bot.db.session import async_session_maker
from bot.db.models import Product, ProductType, Look
from bot.keyboards.inline import corset_looks_kb, look_detail_kb
from bot.utils.texts import CORSET_LOOKS_INTRO, LOOK_DESCRIPTIONS


router = Router(name='corset_looks')


@router.callback_query(F.data == 'corset:looks')
async def cb_looks(call: CallbackQuery) -> None:
    """Показывает доступные образы. Если фото загружены – из БД, иначе – дефолтные ключи."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(Product).where(
                Product.type == ProductType.CORSET,
                Product.is_active == True,
                Product.look.is_not(None),
            ).order_by(Product.sort_order, Product.id)
        )
        products = list(result.scalars().all())

    if products:
        keys = []
        for p in products:
            if p.look and p.look.value not in keys:
                keys.append(p.look.value)
        # маппим Look enum → ключи из LOOK_DESCRIPTIONS
    else:
        # пока админ не загрузил – показываем демо-набор
        keys = list(LOOK_DESCRIPTIONS.keys())

    await call.message.edit_text(CORSET_LOOKS_INTRO, reply_markup=corset_looks_kb(keys))
    await call.answer()


@router.callback_query(F.data.startswith('look:show:'))
async def cb_look_show(call: CallbackQuery) -> None:
    look_key = call.data.split(':')[-1]

    # пытаемся найти товар с этим луком
    async with async_session_maker() as session:
        result = await session.execute(
            select(Product).where(
                Product.type == ProductType.CORSET,
                Product.is_active == True,
            ).order_by(Product.sort_order, Product.id)
        )
        products = list(result.scalars().all())

    matching = [p for p in products if p.look and p.look.value == look_key]
    description = LOOK_DESCRIPTIONS.get(look_key, '<i>Описание скоро появится</i>')

    if matching:
        product = matching[0]
        caption = f'{description}\n\n💰 <b>от {product.base_price} BYN</b>'
        # отправляем новое сообщение с фото (нельзя edit_text → edit_media для текстового)
        await call.message.delete()
        await call.message.answer_photo(
            photo=product.image_url,
            caption=caption,
            reply_markup=look_detail_kb(look_key),
        )
    else:
        # пока фото нет – просто текст
        await call.message.edit_text(
            description + '\n\n<i>📸 Фото скоро появится</i>',
            reply_markup=look_detail_kb(look_key),
        )
    await call.answer()
