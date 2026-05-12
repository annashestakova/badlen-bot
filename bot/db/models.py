from typing import Optional
"""SQLAlchemy 2.0 модели — единый источник правды по БД."""

from datetime import datetime, date, time
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import (
    BigInteger, String, Text, Numeric, DateTime, Date, Time, Boolean,
    ForeignKey, Enum as SAEnum, JSON, Integer, UniqueConstraint
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ---------- ENUMS ----------

class ProductType(str, PyEnum):
    WEDDING = 'wedding'      # свадебное платье
    EVENING = 'evening'      # вечернее платье
    CORSET = 'corset'        # корсет


class FabricCategory(str, PyEnum):
    LACE = 'lace'            # кружево
    SATIN = 'satin'          # атлас
    CHIFFON = 'chiffon'      # шифон
    VELVET = 'velvet'        # бархат
    BROCADE = 'brocade'      # парча
    SILK = 'silk'            # шёлк
    OTHER = 'other'


class OrderStatus(str, PyEnum):
    NEW = 'new'                          # только что создан
    AWAITING_FITTING = 'awaiting_fitting' # ждёт записи на примерку
    IN_PROGRESS = 'in_progress'          # в работе
    READY = 'ready'                      # готов
    DELIVERED = 'delivered'              # выдан
    CANCELLED = 'cancelled'              # отменён


class FittingStatus(str, PyEnum):
    REQUESTED = 'requested'    # клиент выбрал слот
    CONFIRMED = 'confirmed'    # админ подтвердил
    DECLINED = 'declined'      # админ отказал
    DONE = 'done'              # примерка прошла


class Look(str, PyEnum):
    CASUAL = 'casual'
    OFFICE = 'office'
    EVENING = 'evening'
    SUMMER = 'summer'
    WINTER = 'winter'
    PARTY = 'party'
    BRIDAL = 'bridal'


# ---------- USERS ----------

class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64))
    first_name: Mapped[str | None] = mapped_column(String(128))
    phone: Mapped[str | None] = mapped_column(String(32))
    email: Mapped[str | None] = mapped_column(String(128))
    consent_personal_data: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    orders: Mapped[list['Order']] = relationship(back_populates='user', cascade='all, delete-orphan')
    measurements: Mapped[list['CorsetMeasurement']] = relationship(back_populates='user', cascade='all, delete-orphan')


# ---------- FABRICS (с decobay.by) ----------

class Fabric(Base):
    __tablename__ = 'fabrics'

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str | None] = mapped_column(String(128), index=True)  # id с decobay
    name: Mapped[str] = mapped_column(String(255))
    category: Mapped[FabricCategory] = mapped_column(SAEnum(FabricCategory))
    color: Mapped[str | None] = mapped_column(String(64))
    price_per_meter: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    description: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(512))
    source_url: Mapped[str | None] = mapped_column(String(512))
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------- PRODUCTS (модели платьев и корсетов от админа) ----------

class Product(Base):
    """Модель платья/корсета с фото — то что админ загружает в галерею."""
    __tablename__ = 'products'

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[ProductType] = mapped_column(SAEnum(ProductType))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    base_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    image_url: Mapped[str] = mapped_column(String(512))
    look: Mapped[Look | None] = mapped_column(SAEnum(Look))  # для корсетных луков
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ---------- ORDERS ----------

class Order(Base):
    __tablename__ = 'orders'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    type: Mapped[ProductType] = mapped_column(SAEnum(ProductType))
    status: Mapped[OrderStatus] = mapped_column(SAEnum(OrderStatus), default=OrderStatus.NEW)

    # Калькуляция (JSON чтобы гибко)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    total_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    # Контакты (могут отличаться от профиля)
    contact_phone: Mapped[str | None] = mapped_column(String(32))
    contact_email: Mapped[str | None] = mapped_column(String(128))
    contact_name: Mapped[str | None] = mapped_column(String(128))

    # Для корсетов — адрес доставки
    delivery_address: Mapped[str | None] = mapped_column(Text)

    # Срочность
    is_urgent: Mapped[bool] = mapped_column(Boolean, default=False)

    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped['User'] = relationship(back_populates='orders')
    fittings: Mapped[list['Fitting']] = relationship(back_populates='order', cascade='all, delete-orphan')


# ---------- FITTINGS (примерки в Бресте) ----------

class FittingSlot(Base):
    """Доступные слоты на примерку — админ создаёт, клиент выбирает."""
    __tablename__ = 'fitting_slots'
    __table_args__ = (UniqueConstraint('slot_date', 'slot_time', name='uq_slot'),)

    id: Mapped[int] = mapped_column(primary_key=True)
    slot_date: Mapped[date] = mapped_column(Date, index=True)
    slot_time: Mapped[time] = mapped_column(Time)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Fitting(Base):
    __tablename__ = 'fittings'

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey('orders.id', ondelete='CASCADE'))
    slot_id: Mapped[int] = mapped_column(ForeignKey('fitting_slots.id'))
    status: Mapped[FittingStatus] = mapped_column(SAEnum(FittingStatus), default=FittingStatus.REQUESTED)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    order: Mapped['Order'] = relationship(back_populates='fittings')
    slot: Mapped['FittingSlot'] = relationship()


# ---------- CORSET MEASUREMENTS ----------

class CorsetMeasurement(Base):
    """Поэтапно собранные мерки клиента для корсета."""
    __tablename__ = 'corset_measurements'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    order_id: Mapped[int | None] = mapped_column(ForeignKey('orders.id', ondelete='SET NULL'))

    bust: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))         # 1. обхват груди
    bra_size: Mapped[str | None] = mapped_column(String(16))             # 2. размер бюстгальтера
    under_bust: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))    # 3. под грудью
    waist: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))         # 4. талия
    desired_tight: Mapped[Decimal | None] = mapped_column(Numeric(5, 2)) # 5. желаемая утяжка
    belly: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))         # обхват живота
    hips: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))          # 6. бёдра
    waist_to_under_bust: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))  # 7. талия-под грудью
    figure_notes: Mapped[str | None] = mapped_column(Text)               # 8. что не нравится

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped['User'] = relationship(back_populates='measurements')


# ---------- SETTINGS (KV для админа: цены, тексты) ----------

class Setting(Base):
    __tablename__ = 'settings'

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
