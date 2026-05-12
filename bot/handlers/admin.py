from typing import Optional
"""Админ-панель: заявки, примерки, слоты, загрузка фото, обновление тканей."""

import io
import re
from datetime import date as date_t, time as time_t, datetime
from decimal import Decimal, InvalidOperation

from aiogram import Router, F, BaseMiddleware
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery, TelegramObject
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger
from sqlalchemy import select

from bot.config import settings
from bot.db.session import async_session_maker
from bot.db.models import (
    Order, OrderStatus, FittingSlot, Fitting, FittingStatus,
    Product, ProductType, Look, User,
)
from bot.keyboards.inline import admin_panel_kb, main_menu_kb
from bot.services.blob import upload_to_blob
from bot.states.order import AdminAddSlot, AdminAddProduct
from bot.utils.texts import ADMIN_PANEL
from bot.utils.validators import sanitize_text


router = Router(name='admin')


# ---------- ФИЛЬТР АДМИНА (для всего роутера) ----------

class AdminMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data: dict):
        user = None
        if isinstance(event, (Message, CallbackQuery)) and event.from_user:
            user = event.from_user
        if not user or user.id not in settings.admin_ids:
            if isinstance(event, CallbackQuery):
                await event.answer('Только для админа', show_alert=True)
            elif isinstance(event, Message):
                pass  # молча игнорим
            return None
        return await handler(event, data)


router.message.middleware(AdminMiddleware())
router.callback_query.middleware(AdminMiddleware())


# ---------- ВХОД ----------

@router.message(Command('admin'))
async def cmd_admin(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(ADMIN_PANEL, reply_markup=admin_panel_kb())


@router.callback_query(F.data == 'admin:panel')
async def cb_admin_panel(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_text(ADMIN_PANEL, reply_markup=admin_panel_kb())
    await call.answer()


# ---------- СПИСОК ЗАЯВОК ----------

@router.callback_query(F.data == 'admin:orders:list')
async def cb_orders_list(call: CallbackQuery) -> None:
    async with async_session_maker() as session:
        result = await session.execute(
            select(Order).where(
                Order.status.in_([OrderStatus.NEW, OrderStatus.AWAITING_FITTING, OrderStatus.IN_PROGRESS])
            ).order_by(Order.created_at.desc()).limit(20)
        )
        orders = list(result.scalars().all())

    b = InlineKeyboardBuilder()
    if not orders:
        text = '📋 <b>Открытых заявок нет</b>'
    else:
        lines = ['📋 <b>Открытые заявки</b>\n']
        type_emoji = {ProductType.WEDDING: '👰🏻‍♀️', ProductType.EVENING: '🥂', ProductType.CORSET: '🎀'}
        status_label = {
            OrderStatus.NEW: 'новая',
            OrderStatus.AWAITING_FITTING: 'примерка',
            OrderStatus.IN_PROGRESS: 'в работе',
        }
        for o in orders:
            lines.append(
                f'{type_emoji.get(o.type, "•")} <b>№{o.id}</b> '
                f'– {status_label.get(o.status, o.status.value)} '
                f'– {o.total_price} BYN'
            )
            b.button(text=f'№{o.id} ({o.total_price} BYN)', callback_data=f'admin:order:view:{o.id}')
        text = '\n'.join(lines)
    b.button(text='⬅️ В админку', callback_data='admin:panel')
    b.adjust(1)
    await call.message.edit_text(text, reply_markup=b.as_markup())
    await call.answer()


@router.callback_query(F.data.startswith('admin:order:view:'))
async def cb_order_view(call: CallbackQuery) -> None:
    order_id = int(call.data.split(':')[-1])
    async with async_session_maker() as session:
        order = await session.get(Order, order_id)
        user = await session.get(User, order.user_id) if order else None

    if not order or not user:
        await call.answer('Заявка не найдена', show_alert=True)
        return

    type_label = {
        ProductType.WEDDING: '👰🏻‍♀️ Свадебное',
        ProductType.EVENING: '🥂 Вечернее',
        ProductType.CORSET: '🎀 Корсет',
    }.get(order.type, order.type.value)

    import json
    config_pretty = json.dumps(order.config, ensure_ascii=False, indent=2, default=str)[:1500]

    text = (
        f'<b>Заявка №{order.id}</b>\n\n'
        f'<b>Тип:</b> {type_label}\n'
        f'<b>Статус:</b> {order.status.value}\n'
        f'<b>Клиент:</b> {order.contact_name or user.first_name or "—"} (@{user.username or "—"})\n'
        f'<b>TG ID:</b> <code>{user.tg_id}</code>\n'
        f'<b>Телефон:</b> {order.contact_phone or "—"}\n'
        f'<b>Email:</b> {order.contact_email or "—"}\n'
        f'<b>Адрес:</b> {order.delivery_address or "—"}\n'
        f'<b>Срочно:</b> {"да" if order.is_urgent else "нет"}\n\n'
        f'<b>Конфиг:</b>\n<pre>{config_pretty}</pre>\n\n'
        f'💰 <b>Сумма: {order.total_price} BYN</b>'
    )

    b = InlineKeyboardBuilder()
    b.button(text='💬 Связаться', url=f'tg://user?id={user.tg_id}')
    b.button(text='✅ В работу', callback_data=f'admin:order:accept:{order.id}')
    b.button(text='✔️ Готов', callback_data=f'admin:order:ready:{order.id}')
    b.button(text='📦 Выдан', callback_data=f'admin:order:delivered:{order.id}')
    b.button(text='❌ Отменить', callback_data=f'admin:order:cancel:{order.id}')
    b.button(text='⬅️ К списку', callback_data='admin:orders:list')
    b.adjust(1, 2, 2, 1)
    await call.message.edit_text(text, reply_markup=b.as_markup())
    await call.answer()


@router.callback_query(F.data.regexp(r'^admin:order:(accept|ready|delivered|cancel):\d+$'))
async def cb_order_status(call: CallbackQuery) -> None:
    parts = call.data.split(':')
    action = parts[2]
    order_id = int(parts[3])

    status_map = {
        'accept': OrderStatus.IN_PROGRESS,
        'ready': OrderStatus.READY,
        'delivered': OrderStatus.DELIVERED,
        'cancel': OrderStatus.CANCELLED,
    }
    new_status = status_map[action]

    async with async_session_maker() as session:
        order = await session.get(Order, order_id)
        if not order:
            await call.answer('Заявка не найдена', show_alert=True)
            return
        order.status = new_status
        user = await session.get(User, order.user_id)
        await session.commit()
        client_tg = user.tg_id if user else None

    # уведомление клиенту по ключевым переходам
    notify_text = {
        OrderStatus.IN_PROGRESS: f'✨ Ваша заявка №{order_id} принята в работу. Скоро свяжусь с деталями.',
        OrderStatus.READY: f'🎉 Заказ №{order_id} готов! Я свяжусь с вами для отправки или примерки.',
        OrderStatus.DELIVERED: f'🤍 Спасибо за заказ №{order_id}! Будем рады видеть вас снова.',
        OrderStatus.CANCELLED: f'🌸 Заявка №{order_id} отменена. Если это ошибка – напишите мне.',
    }.get(new_status)
    if client_tg and notify_text:
        try:
            await call.bot.send_message(client_tg, notify_text)
        except Exception:
            pass

    await call.answer(f'Статус изменён: {new_status.value}')
    # перерисуем карточку
    call.data = f'admin:order:view:{order_id}'
    await cb_order_view(call)


# ---------- ПРИМЕРКИ ----------

@router.callback_query(F.data == 'admin:fittings:list')
async def cb_fittings_list(call: CallbackQuery) -> None:
    async with async_session_maker() as session:
        result = await session.execute(
            select(Fitting).where(Fitting.status == FittingStatus.REQUESTED)
            .order_by(Fitting.created_at.desc()).limit(20)
        )
        fittings = list(result.scalars().all())

    b = InlineKeyboardBuilder()
    if not fittings:
        text = '📅 <b>Запросов на примерку нет</b>'
    else:
        lines = ['📅 <b>Запросы на примерку (ожидают подтверждения)</b>\n']
        for f in fittings:
            slot = await _get_slot(f.slot_id)
            if slot:
                lines.append(
                    f'• №{f.order_id} – {slot.slot_date.strftime("%d.%m")} {slot.slot_time.strftime("%H:%M")}'
                )
                b.button(
                    text=f'№{f.order_id} {slot.slot_date.strftime("%d.%m")} {slot.slot_time.strftime("%H:%M")}',
                    callback_data=f'admin:fit:view:{f.id}',
                )
        text = '\n'.join(lines)
    b.button(text='⬅️ В админку', callback_data='admin:panel')
    b.adjust(1)
    await call.message.edit_text(text, reply_markup=b.as_markup())
    await call.answer()


async def _get_slot(slot_id: int):
    async with async_session_maker() as session:
        return await session.get(FittingSlot, slot_id)


@router.callback_query(F.data.startswith('admin:fit:view:'))
async def cb_fit_view(call: CallbackQuery) -> None:
    fitting_id = int(call.data.split(':')[-1])
    async with async_session_maker() as session:
        f = await session.get(Fitting, fitting_id)
        if not f:
            await call.answer('Заявка не найдена', show_alert=True)
            return
        order = await session.get(Order, f.order_id)
        user = await session.get(User, order.user_id) if order else None
        slot = await session.get(FittingSlot, f.slot_id)

    text = (
        f'📅 <b>Примерка №{fitting_id}</b>\n\n'
        f'<b>Заказ:</b> №{f.order_id}\n'
        f'<b>Клиент:</b> {user.first_name or "—"} (@{user.username or "—"})\n'
        f'<b>TG ID:</b> <code>{user.tg_id}</code>\n'
        f'<b>Телефон:</b> {order.contact_phone or user.phone or "—"}\n\n'
        f'📅 <b>{slot.slot_date.strftime("%d.%m.%Y")}</b> в <b>{slot.slot_time.strftime("%H:%M")}</b>\n'
        f'<b>Статус:</b> {f.status.value}'
    )

    b = InlineKeyboardBuilder()
    b.button(text='💬 Связаться', url=f'tg://user?id={user.tg_id}')
    b.button(text='✅ Подтвердить', callback_data=f'admin:fit:confirm:{f.id}')
    b.button(text='❌ Отклонить', callback_data=f'admin:fit:decline:{f.id}')
    b.button(text='⬅️ К списку', callback_data='admin:fittings:list')
    b.adjust(1, 2, 1)
    await call.message.edit_text(text, reply_markup=b.as_markup())
    await call.answer()


# ---------- ДОБАВЛЕНИЕ СЛОТА ----------

@router.callback_query(F.data == 'admin:slot:add')
async def cb_slot_add(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminAddSlot.waiting_date)
    b = InlineKeyboardBuilder()
    b.button(text='❌ Отмена', callback_data='admin:panel')
    await call.message.edit_text(
        '➕ <b>Новый слот</b>\n\n'
        'Введите дату в формате <code>ДД.ММ.ГГГГ</code>\n'
        'Пример: <code>25.05.2026</code>',
        reply_markup=b.as_markup(),
    )
    await call.answer()


@router.message(StateFilter(AdminAddSlot.waiting_date), F.text)
async def msg_slot_date(message: Message, state: FSMContext) -> None:
    try:
        d = datetime.strptime(message.text.strip(), '%d.%m.%Y').date()
    except ValueError:
        await message.answer('❌ Не получилось распарсить дату. Формат: <code>25.05.2026</code>')
        return
    if d < date_t.today():
        await message.answer('❌ Дата в прошлом, не подходит.')
        return
    await state.update_data(slot_date=d.isoformat())
    await state.set_state(AdminAddSlot.waiting_time)
    await message.answer(
        '⏰ Теперь введите время в формате <code>ЧЧ:ММ</code>\n'
        'Можно несколько через запятую: <code>10:00, 12:00, 14:00, 16:00, 18:00</code>'
    )


@router.message(StateFilter(AdminAddSlot.waiting_time), F.text)
async def msg_slot_time(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    d = date_t.fromisoformat(data['slot_date'])

    times: list[time_t] = []
    for chunk in message.text.split(','):
        chunk = chunk.strip()
        try:
            t = datetime.strptime(chunk, '%H:%M').time()
            times.append(t)
        except ValueError:
            await message.answer(f'❌ Не распарсилось: <code>{chunk}</code>. Формат: <code>10:00</code>')
            return

    if not times:
        await message.answer('❌ Не вижу ни одного времени.')
        return

    added = 0
    skipped = 0
    async with async_session_maker() as session:
        for t in times:
            exists = await session.execute(
                select(FittingSlot).where(
                    FittingSlot.slot_date == d,
                    FittingSlot.slot_time == t,
                )
            )
            if exists.scalar_one_or_none():
                skipped += 1
                continue
            session.add(FittingSlot(slot_date=d, slot_time=t, is_available=True))
            added += 1
        await session.commit()

    await state.clear()
    await message.answer(
        f'✅ Добавлено: <b>{added}</b>, пропущено (уже есть): <b>{skipped}</b>',
        reply_markup=admin_panel_kb(),
    )


# ---------- ЗАГРУЗКА ФОТО (товаров и луков) ----------

@router.callback_query(F.data == 'admin:photo:add')
async def cb_photo_add(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminAddProduct.waiting_type)
    b = InlineKeyboardBuilder()
    b.button(text='👰🏻‍♀️ Свадебное', callback_data='admin:photo:type:wedding')
    b.button(text='🥂 Вечернее', callback_data='admin:photo:type:evening')
    b.button(text='🎀 Корсет (лук)', callback_data='admin:photo:type:corset')
    b.button(text='❌ Отмена', callback_data='admin:panel')
    b.adjust(1)
    await call.message.edit_text(
        '📸 <b>Загрузить фото в галерею</b>\n\nВыберите тип:',
        reply_markup=b.as_markup(),
    )
    await call.answer()


@router.callback_query(F.data.startswith('admin:photo:type:'), StateFilter(AdminAddProduct.waiting_type))
async def cb_photo_type(call: CallbackQuery, state: FSMContext) -> None:
    type_key = call.data.split(':')[-1]
    type_map = {
        'wedding': ProductType.WEDDING,
        'evening': ProductType.EVENING,
        'corset': ProductType.CORSET,
    }
    await state.update_data(p_type=type_map[type_key].value)
    await state.set_state(AdminAddProduct.waiting_title)
    await call.message.edit_text('✍️ Введите название модели:')
    await call.answer()


@router.message(StateFilter(AdminAddProduct.waiting_title), F.text)
async def msg_photo_title(message: Message, state: FSMContext) -> None:
    title = sanitize_text(message.text, max_len=255)
    if len(title) < 2:
        await message.answer('❌ Слишком короткое.')
        return
    await state.update_data(p_title=title)
    await state.set_state(AdminAddProduct.waiting_description)
    await message.answer('✍️ Введите описание (или - чтобы пропустить):')


@router.message(StateFilter(AdminAddProduct.waiting_description), F.text)
async def msg_photo_description(message: Message, state: FSMContext) -> None:
    desc = sanitize_text(message.text, max_len=1000)
    if desc == '-':
        desc = None
    await state.update_data(p_description=desc)
    await state.set_state(AdminAddProduct.waiting_price)
    await message.answer('💰 Введите базовую цену в BYN:')


@router.message(StateFilter(AdminAddProduct.waiting_price), F.text)
async def msg_photo_price(message: Message, state: FSMContext) -> None:
    try:
        price = Decimal(message.text.replace(',', '.').strip())
    except InvalidOperation:
        await message.answer('❌ Не число. Например: <code>450</code>')
        return
    await state.update_data(p_price=str(price))

    data = await state.get_data()
    if data.get('p_type') == ProductType.CORSET.value:
        # для корсета спрашиваем лук
        await state.set_state(AdminAddProduct.waiting_look)
        b = InlineKeyboardBuilder()
        look_labels = {
            'casual': '☕ Casual',
            'office': '🤍 Office',
            'evening': '🥂 Evening',
            'summer': '🌸 Summer',
            'winter': '❄️ Winter',
            'party': '✨ Party',
            'bridal': '👰 Bridal',
        }
        for key, label in look_labels.items():
            b.button(text=label, callback_data=f'admin:look:{key}')
        b.button(text='Без лука', callback_data='admin:look:none')
        b.adjust(2)
        await message.answer('✨ К какому луку относится корсет?', reply_markup=b.as_markup())
    else:
        await state.update_data(p_look=None)
        await state.set_state(AdminAddProduct.waiting_photo)
        await message.answer('📸 Пришлите фото:')


@router.callback_query(F.data.startswith('admin:look:'), StateFilter(AdminAddProduct.waiting_look))
async def cb_photo_look(call: CallbackQuery, state: FSMContext) -> None:
    look_key = call.data.split(':')[-1]
    await state.update_data(p_look=look_key if look_key != 'none' else None)
    await state.set_state(AdminAddProduct.waiting_photo)
    await call.message.edit_text('📸 Пришлите фото:')
    await call.answer()


@router.message(StateFilter(AdminAddProduct.waiting_photo), F.photo)
async def msg_photo_received(message: Message, state: FSMContext) -> None:
    data = await state.get_data()

    # берём самое большое разрешение
    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    buf = io.BytesIO()
    await message.bot.download(file, destination=buf)
    buf.seek(0)

    # имя для Blob: ptype_timestamp.jpg
    ts = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    filename = f'{data["p_type"]}_{ts}.jpg'

    public_url = await upload_to_blob(filename, buf.read(), content_type='image/jpeg')
    if not public_url:
        await message.answer('❌ Не удалось загрузить в Blob. Проверь токен.', reply_markup=admin_panel_kb())
        await state.clear()
        return

    type_map = {'wedding': ProductType.WEDDING, 'evening': ProductType.EVENING, 'corset': ProductType.CORSET}
    look_map = {
        'casual': Look.CASUAL, 'office': Look.OFFICE, 'evening': Look.EVENING,
        'summer': Look.SUMMER, 'winter': Look.WINTER, 'party': Look.PARTY, 'bridal': Look.BRIDAL,
    }
    look_value = look_map.get(data.get('p_look')) if data.get('p_look') else None

    async with async_session_maker() as session:
        product = Product(
            type=type_map[data['p_type']],
            title=data['p_title'],
            description=data.get('p_description'),
            base_price=Decimal(data['p_price']),
            image_url=public_url,
            look=look_value,
            is_active=True,
        )
        session.add(product)
        await session.commit()
        await session.refresh(product)

    await state.clear()
    await message.answer_photo(
        photo=public_url,
        caption=(
            f'✅ <b>Сохранено</b>\n\n'
            f'<b>{product.title}</b>\n'
            f'Тип: {product.type.value} · {product.base_price} BYN\n'
            f'ID: {product.id}'
        ),
        reply_markup=admin_panel_kb(),
    )


# ---------- ЗАПУСК ПАРСЕРА ТКАНЕЙ ----------

@router.callback_query(F.data == 'admin:fabrics:refresh')
async def cb_fabrics_refresh(call: CallbackQuery) -> None:
    await call.answer('Запускаю парсер... может занять минуту', show_alert=True)
    try:
        from bot.services.decobay_parser import run_parser
        count = await run_parser()
        await call.message.answer(
            f'✅ Парсер отработал. Обновлено тканей: <b>{count}</b>',
            reply_markup=admin_panel_kb(),
        )
    except Exception as e:
        logger.exception(f'Parser failed: {e}')
        await call.message.answer(
            f'❌ Парсер упал: <code>{str(e)[:200]}</code>',
            reply_markup=admin_panel_kb(),
        )
