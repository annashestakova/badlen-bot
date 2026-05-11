"""Прайсинг — вся бизнес-логика расчётов.

Базовые цены настраиваются в БД (таблица Setting), но дефолты здесь.
Админ может менять через админ-панель."""

from decimal import Decimal
from typing import Optional


# ==========================================
# СВАДЕБНЫЕ ПЛАТЬЯ
# ==========================================

WEDDING_BASE_PRICES = {
    'short_simple': Decimal('700'),       # короткое простое
    'midi': Decimal('1100'),              # миди
    'long_simple': Decimal('1400'),       # длинное простое
    'long_decor': Decimal('1900'),        # длинное с декором
    'trail': Decimal('2400'),             # с шлейфом
    'premium': Decimal('3200'),           # премиум, многослойное
}

WEDDING_BASE_LABELS = {
    'short_simple': '🤍 Короткое простое',
    'midi': '🤍 Миди',
    'long_simple': '🤍 Длинное простое',
    'long_decor': '🤍 Длинное с декором',
    'trail': '🤍 Со шлейфом',
    'premium': '🤍 Премиум',
}


# ==========================================
# ВЕЧЕРНИЕ ПЛАТЬЯ
# ==========================================

EVENING_BASE_PRICES = {
    'mini': Decimal('400'),
    'midi_simple': Decimal('550'),
    'midi_decor': Decimal('750'),
    'long_simple': Decimal('900'),
    'long_decor': Decimal('1300'),
    'gown': Decimal('1800'),
}

EVENING_BASE_LABELS = {
    'mini': '🥂 Мини',
    'midi_simple': '🥂 Миди простое',
    'midi_decor': '🥂 Миди с декором',
    'long_simple': '🥂 Длинное простое',
    'long_decor': '🥂 Длинное с декором',
    'gown': '🥂 Вечернее платье premium',
}


# ==========================================
# ОПЦИИ К ПЛАТЬЯМ (общие)
# ==========================================

DRESS_OPTIONS = {
    'corset_lacing': {'label': '🎀 Корсет на шнуровке', 'price': Decimal('150')},
    'open_back': {'label': '🌙 Открытая спина', 'price': Decimal('80')},
    'detachable_skirt': {'label': '✨ Съёмная юбка', 'price': Decimal('300')},
    'embroidery_simple': {'label': '🌸 Простая вышивка', 'price': Decimal('200')},
    'embroidery_rich': {'label': '🌸 Богатая вышивка', 'price': Decimal('500')},
    'beading': {'label': '💎 Бусины / жемчуг', 'price': Decimal('250')},
    'lace_decor': {'label': '🌸 Кружевной декор', 'price': Decimal('200')},
    'veil': {'label': '👰 Фата в комплект', 'price': Decimal('180')},
    'sleeves': {'label': '🤍 Рукава', 'price': Decimal('120')},
    'gloves': {'label': '🧤 Перчатки в комплект', 'price': Decimal('80')},
}


# ==========================================
# КОРСЕТЫ
# ==========================================

CORSET_TYPES = {
    'underbust': {
        'label': '🎀 Под грудь (классический)',
        'price': Decimal('120'),
        'description': 'Заканчивается под грудью, носится с топом или платьем',
    },
    'overbust': {
        'label': '🎀 С чашками (полноценный)',
        'price': Decimal('180'),
        'description': 'Закрывает грудь, можно носить как самостоятельный верх',
    },
    'midi_corset': {
        'label': '✨ Миди-корсет с баской',
        'price': Decimal('220'),
        'description': 'С баской или пеплумом – элегантно, для офиса и торжеств',
    },
    'bridal': {
        'label': '👰 Свадебный (отдельный)',
        'price': Decimal('280'),
        'description': 'Для невест – белый, кружево, жемчуг, шнуровка',
    },
    'with_straps': {
        'label': '🌸 С лентами на плечах',
        'price': Decimal('150'),
        'description': 'Лёгкий вариант с атласными лентами-завязками',
    },
}

CORSET_CLOSURE = {
    'lacing_back': {'label': '🎀 Шнуровка сзади', 'price': Decimal('30')},
    'lacing_front': {'label': '🎀 Шнуровка спереди', 'price': Decimal('40')},
    'lacing_both': {'label': '🎀 Шнуровка с двух сторон', 'price': Decimal('50')},
    'zipper': {'label': '⚡ Молния (скрытая)', 'price': Decimal('25')},
    'busk': {'label': '🔱 Бюск-замок (металлический)', 'price': Decimal('45')},
    'hooks_zip': {'label': '🔱 Крючки + молния', 'price': Decimal('55')},
}

CORSET_OPTIONS = {
    'busk_bones': {'label': '🦴 Усиленные косточки', 'price': Decimal('40')},
    'lining_silk': {'label': '🌙 Шёлковая подкладка', 'price': Decimal('60')},
    'embroidery': {'label': '🌸 Ручная вышивка', 'price': Decimal('120')},
    'beading': {'label': '💎 Бусины / жемчуг', 'price': Decimal('100')},
    'peplum': {'label': '✨ Баска / пеплум', 'price': Decimal('80')},
    'gift_wrap': {'label': '🎁 Подарочная упаковка', 'price': Decimal('25')},
}

CORSET_BASE_FABRIC_METERS = Decimal('1.5')  # сколько ткани в среднем на корсет


# ==========================================
# СРОЧНОСТЬ
# ==========================================

URGENT_MULTIPLIER = Decimal('1.30')  # +30% при срочном пошиве


# ==========================================
# CALCULATORS
# ==========================================

class DressCalculator:
    """Калькулятор пошива платья. Хранит конфиг и считает итог."""

    def __init__(self, base_type: str, is_wedding: bool):
        self.is_wedding = is_wedding
        self.base_type = base_type
        self.options: list[str] = []
        self.is_urgent = False

    @property
    def base_price(self) -> Decimal:
        if self.is_wedding:
            return WEDDING_BASE_PRICES.get(self.base_type, Decimal('0'))
        return EVENING_BASE_PRICES.get(self.base_type, Decimal('0'))

    @property
    def base_label(self) -> str:
        if self.is_wedding:
            return WEDDING_BASE_LABELS.get(self.base_type, self.base_type)
        return EVENING_BASE_LABELS.get(self.base_type, self.base_type)

    def toggle_option(self, key: str) -> None:
        if key in self.options:
            self.options.remove(key)
        else:
            self.options.append(key)

    def options_total(self) -> Decimal:
        return sum((DRESS_OPTIONS[k]['price'] for k in self.options if k in DRESS_OPTIONS), Decimal('0'))

    def total(self) -> Decimal:
        subtotal = self.base_price + self.options_total()
        if self.is_urgent:
            subtotal = subtotal * URGENT_MULTIPLIER
        return subtotal.quantize(Decimal('0.01'))

    def summary(self) -> str:
        lines = [self.base_label + f' – {self.base_price} BYN']
        for k in self.options:
            opt = DRESS_OPTIONS.get(k)
            if opt:
                lines.append(f'{opt["label"]} – +{opt["price"]} BYN')
        if self.is_urgent:
            lines.append(f'⚡ Срочный пошив – +30%')
        return '\n'.join(lines)

    def to_dict(self) -> dict:
        return {
            'kind': 'wedding' if self.is_wedding else 'evening',
            'base_type': self.base_type,
            'options': self.options,
            'is_urgent': self.is_urgent,
            'total': str(self.total()),
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'DressCalculator':
        calc = cls(data['base_type'], data.get('kind') == 'wedding')
        calc.options = data.get('options', [])
        calc.is_urgent = data.get('is_urgent', False)
        return calc


class CorsetCalculator:
    """Калькулятор корсета."""

    def __init__(self):
        self.corset_type: Optional[str] = None
        self.fabric_id: Optional[int] = None
        self.fabric_name: Optional[str] = None
        self.fabric_price_per_m: Optional[Decimal] = None
        self.closure: Optional[str] = None
        self.options: list[str] = []
        self.is_urgent = False

    @property
    def base_price(self) -> Decimal:
        if not self.corset_type:
            return Decimal('0')
        return CORSET_TYPES.get(self.corset_type, {}).get('price', Decimal('0'))

    def fabric_cost(self) -> Decimal:
        if self.fabric_price_per_m is None:
            return Decimal('0')
        return (Decimal(self.fabric_price_per_m) * CORSET_BASE_FABRIC_METERS).quantize(Decimal('0.01'))

    def closure_cost(self) -> Decimal:
        if not self.closure:
            return Decimal('0')
        return CORSET_CLOSURE.get(self.closure, {}).get('price', Decimal('0'))

    def options_total(self) -> Decimal:
        return sum((CORSET_OPTIONS[k]['price'] for k in self.options if k in CORSET_OPTIONS), Decimal('0'))

    def total(self) -> Decimal:
        subtotal = self.base_price + self.fabric_cost() + self.closure_cost() + self.options_total()
        if self.is_urgent:
            subtotal = subtotal * URGENT_MULTIPLIER
        return subtotal.quantize(Decimal('0.01'))

    def summary(self) -> str:
        lines = []
        if self.corset_type:
            t = CORSET_TYPES[self.corset_type]
            lines.append(f'{t["label"]} – {t["price"]} BYN')
        if self.fabric_name and self.fabric_price_per_m is not None:
            lines.append(
                f'🪡 Ткань: {self.fabric_name} '
                f'({self.fabric_price_per_m} BYN/м × {CORSET_BASE_FABRIC_METERS} м) '
                f'– {self.fabric_cost()} BYN'
            )
        if self.closure:
            c = CORSET_CLOSURE[self.closure]
            lines.append(f'{c["label"]} – +{c["price"]} BYN')
        for k in self.options:
            opt = CORSET_OPTIONS.get(k)
            if opt:
                lines.append(f'{opt["label"]} – +{opt["price"]} BYN')
        if self.is_urgent:
            lines.append('⚡ Срочный пошив – +30%')
        return '\n'.join(lines) if lines else '<i>пока ничего не выбрано</i>'

    def to_dict(self) -> dict:
        return {
            'corset_type': self.corset_type,
            'fabric_id': self.fabric_id,
            'fabric_name': self.fabric_name,
            'fabric_price_per_m': str(self.fabric_price_per_m) if self.fabric_price_per_m is not None else None,
            'closure': self.closure,
            'options': self.options,
            'is_urgent': self.is_urgent,
            'total': str(self.total()),
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'CorsetCalculator':
        calc = cls()
        calc.corset_type = data.get('corset_type')
        calc.fabric_id = data.get('fabric_id')
        calc.fabric_name = data.get('fabric_name')
        fp = data.get('fabric_price_per_m')
        calc.fabric_price_per_m = Decimal(fp) if fp else None
        calc.closure = data.get('closure')
        calc.options = data.get('options', [])
        calc.is_urgent = data.get('is_urgent', False)
        return calc
