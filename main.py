import asyncio
import httpx
import json
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "8194473719:AAGv2nAUpEFRDd4_L0ufE95CMuZ3omhrniE"
DATA_FILE = "subscriptions.json"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

USD_to_UZS = 11500  # курс

# ============ FSM ============
class AddSub(StatesGroup):
    waiting_for_name = State()
    waiting_for_price = State()
    waiting_for_currency = State()
    waiting_for_day = State()

class MonthCurrency(StatesGroup):
    waiting_for_currency = State()

# ============ JSON ============
def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_after_add_keyboard(lang="ru") -> InlineKeyboardMarkup:
    # Тексты кнопок для разных языков
    button_texts = {
        "ru": ["👉 Добавить ещё", "📋 Посмотреть все подписки", "🏠 В меню"],
        "uz": ["👉 Yana qo‘shish", "📋 Barcha obunalarni ko‘rish", "🏠 Menyuga"],
        "en": ["👉 Add more", "📋 Show all subscriptions", "🏠 Main menu"]
    }

    texts = button_texts.get(lang, button_texts["ru"])

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts[0], callback_data="add_more")],
        [InlineKeyboardButton(text=texts[1], callback_data="show_list")],
        [InlineKeyboardButton(text=texts[2], callback_data="main_menu")]
    ])
    return keyboard


# ====== ОБРАБОТЧИКИ КНОПОК ПОСЛЕ ДОБАВЛЕНИЯ ======
@dp.callback_query(lambda c: c.data == "add_more")
async def add_more_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await add_subscription(callback.message, state)  # запускаем процесс добавления снова

@dp.callback_query(lambda c: c.data == "show_list")
async def show_list_callback(callback: types.CallbackQuery):
    await callback.answer()
    user_id = str(callback.from_user.id)
    data = load_data()
    user_data = data.get(user_id, {"subs": [], "lang": "ru"})
    subs = user_data.get("subs", [])
    lang = user_data.get("lang", "ru")

    if not subs:
        texts = {
            "ru": "У вас пока нет подписок 💡",
            "uz": "Sizda hali obunalar yo‘q 💡",
            "en": "You don't have any subscriptions 💡"
        }
        await callback.message.answer(texts.get(lang, texts["ru"]))
        return

    headers = {
        "ru": "📋 Ваши подписки:\n\n",
        "uz": "📋 Sizning obunalaringiz:\n\n",
        "en": "📋 Your subscriptions:\n\n"
    }
    text = headers.get(lang, headers["ru"])

    for i, s in enumerate(subs, start=1):
        day_texts = {
            "ru": f"списание {s.get('day')} числа",
            "uz": f"to‘lov {s.get('day')} kuni",
            "en": f"billing on {s.get('day')}"
        }
        text += f"{i}. {s.get('name')} — {s.get('price')} {s.get('currency')} — {day_texts.get(lang, day_texts['ru'])}\n"

    await callback.message.answer(text)

@dp.callback_query(lambda c: c.data == "main_menu")
async def main_menu_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await start(callback.message, state)


# ====== ССЫЛКИ ДЛЯ ОТМЕНЫ ======
CANCEL_LINKS = {
    "Netflix": "https://www.netflix.com/cancelplan",
    "Spotify": "https://support.spotify.com/article/cancel-your-subscription/",
    "YouTube Premium": "https://support.google.com/youtube/answer/6306276",
    "Adobe": "https://account.adobe.com/plans",
    "ChatGPT": "https://help.openai.com/en/articles/6825453-how-do-i-cancel-my-subscription",
    "HBO Max": "https://www.hbomax.com/account/cancel",
    "Disney+": "https://www.disneyplus.com/cancel",
    "Amazon Prime": "https://www.amazon.com/gp/help/customer/display.html?nodeId=201910960",
    "Apple Music": "https://support.apple.com/en-us/HT202039",
    "Tidal": "https://support.tidal.com/hc/en-us/articles/215855847-Cancel-your-TIDAL-subscription"
}

# ============ /start ============
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton(text="🇺🇿 O‘zbekcha", callback_data="lang_uz")],
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")]
    ])
    await message.answer("🌐 Выберите язык / Tilni tanlang / Choose your language:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("lang_"))
async def set_language(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    user_id = str(callback.from_user.id)
    data = load_data()
    if user_id not in data or isinstance(data[user_id], list):
        data[user_id] = {"subs": [], "lang": lang}
    else:
        data[user_id]["lang"] = lang
    save_data(data)
    texts = {
        "ru": "✅ Язык установлен: Русский\n\nИспользуйте команды:\n/add — добавить подписку\n/list — список\n/month — расходы за месяц\n/soon — ближайшие списания\n/cancel — отменить подписку",
        "uz": "✅ Til o‘rnatildi: O‘zbekcha\n\nBuyruqlar:\n/add — obuna qo‘shish\n/list — obunalar ro‘yxati\n/month — oylik xarajatlar\n/soon — yaqin to‘lovlar\n/cancel — obunani bekor qilish",
        "en": "✅ Language set: English\n\nCommands:\n/add — add a subscription\n/list — list of subscriptions\n/month — monthly expenses\n/soon — upcoming payments\n/cancel — cancel subscription"
    }
    await callback.message.answer(texts[lang])
    await callback.answer()

# ============ /add ============
@dp.message(Command("add"))
async def add_subscription(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = str(message.from_user.id)
    user_data = load_data().get(user_id, {"subs": [], "lang": "ru"})
    lang = user_data.get("lang", "ru")

    prompts = {
        "ru": "Введите название подписки (например, Netflix):",
        "uz": "Obuna nomini kiriting (masalan, Netflix):",
        "en": "Enter subscription name (e.g., Netflix):"
    }
    await message.answer(prompts.get(lang, prompts["ru"]))
    await state.set_state(AddSub.waiting_for_name)


# ====== Проверка дубликата ======
@dp.message(AddSub.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    user_id = str(message.from_user.id)
    data = load_data()
    user_data = data.get(user_id, {"subs": [], "lang": "ru"})
    lang = user_data.get("lang", "ru")
    subs = user_data.get("subs", [])

    # Тексты для разных языков
    duplicate_texts = {
        "ru": f"⚠ Подписка '{name}' уже есть. Хотите заменить?",
        "uz": f"⚠ '{name}' obunasi allaqachon mavjud. Uni yangilamoqchimisiz?",
        "en": f"⚠ Subscription '{name}' already exists. Do you want to replace it?"
    }
    prompt_price_texts = {
        "ru": "Введите стоимость подписки (например, 10.99):",
        "uz": "Obuna narxini kiriting (masalan, 10.99):",
        "en": "Enter subscription price (e.g., 10.99):"
    }

    # Тексты для кнопок
    button_texts = {
        "ru": ["✅ Да, заменить", "❌ Нет, оставить"],
        "uz": ["✅ Ha, yangilash", "❌ Yo'q, qoldirish"],
        "en": ["✅ Yes, replace", "❌ No, keep"]
    }

    # Проверяем, есть ли такая подписка
    if any(s.get("name", "").lower() == name.lower() for s in subs):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=button_texts.get(lang, button_texts["ru"])[0],
                                     callback_data=f"replace_yes_{name}"),
                InlineKeyboardButton(text=button_texts.get(lang, button_texts["ru"])[1],
                                     callback_data=f"replace_no_{name}")
            ]
        ])
        # Сохраняем имя дубликата во временных данных FSM
        await state.update_data(duplicate_name=name)
        # Отправляем сообщение на выбранном языке
        await message.answer(duplicate_texts.get(lang, duplicate_texts["ru"]), reply_markup=keyboard)
        return  # НЕ очищаем state

    # Если нет дубликата — продолжаем обычный процесс
    await state.update_data(name=name)
    await message.answer(prompt_price_texts.get(lang, prompt_price_texts["ru"]))
    await state.set_state(AddSub.waiting_for_price)

# ====== Callback для кнопок «Да/Нет» ======
@dp.callback_query(lambda c: c.data.startswith("replace_"))
async def process_replace(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    parts = callback.data.split("_", 2)
    action = parts[1]  # yes / no
    duplicate_name = parts[2]  # имя подписки
    user_id = str(callback.from_user.id)
    data = load_data()
    user_data = data.get(user_id, {"subs": [], "lang": "ru"})
    subs = user_data.get("subs", [])
    lang = user_data.get("lang", "ru")

    # Тексты на разных языках
    deleted_texts = {
        "ru": f"Старая подписка '{duplicate_name}' удалена. Введите название новой подписки:",
        "uz": f"'{duplicate_name}' obunasi o‘chirildi. Yangi obuna nomini kiriting:",
        "en": f"Old subscription '{duplicate_name}' removed. Enter the name of the new subscription:"
    }
    kept_texts = {
        "ru": f"Старая подписка '{duplicate_name}' оставлена ✅",
        "uz": f"'{duplicate_name}' obunasi saqlandi ✅",
        "en": f"Old subscription '{duplicate_name}' kept ✅"
    }

    if action == "yes":
        # Удаляем старую подписку
        subs = [s for s in subs if s.get("name", "").lower() != duplicate_name.lower()]
        user_data["subs"] = subs
        data[user_id] = user_data
        save_data(data)

        # Сразу запускаем FSM для добавления новой подписки
        await state.clear()
        await callback.message.answer(deleted_texts.get(lang, deleted_texts["ru"]))
        await state.set_state(AddSub.waiting_for_name)

    else:
        await callback.message.answer(kept_texts.get(lang, kept_texts["ru"]))
        await state.clear()  # очищаем FSM, чтобы не было конфликтов

@dp.message(AddSub.waiting_for_price)
async def process_price(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    data = load_data()
    lang = data.get(user_id, {}).get("lang", "ru")

    try:
        price = float(str(message.text.strip()).replace(" ", "").replace(",", "."))
    except ValueError:
        texts = {
            "ru": "Введите число, например 12.5",
            "uz": "Raqam kiriting, masalan 12.5",
            "en": "Enter a number, e.g., 12.5"
        }
        await message.answer(texts.get(lang, texts["ru"]))
        return

    await state.update_data(price=price)

    texts = {
        "ru": "Введите валюту (USD или UZS):",
        "uz": "Valyutani kiriting (USD yoki UZS):",
        "en": "Enter currency (USD or UZS):"
    }
    await message.answer(texts.get(lang, texts["ru"]))
    await state.set_state(AddSub.waiting_for_currency)


@dp.message(AddSub.waiting_for_currency)
async def process_currency(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    data = load_data()
    lang = data.get(user_id, {}).get("lang", "ru")

    currency = message.text.strip().upper()
    if currency not in ["USD", "UZS"]:
        texts = {
            "ru": "Введите только USD или UZS:",
            "uz": "Faqat USD yoki UZS kiriting:",
            "en": "Enter only USD or UZS:"
        }
        await message.answer(texts.get(lang, texts["ru"]))
        return

    await state.update_data(currency=currency)
    texts = {
        "ru": "Введите день списания (1–31):",
        "uz": "To‘lov kunini kiriting (1–31):",
        "en": "Enter the billing day (1–31):"
    }
    await message.answer(texts.get(lang, texts["ru"]))
    await state.set_state(AddSub.waiting_for_day)

@dp.message(AddSub.waiting_for_day)
async def process_day(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    data = load_data()
    lang = data.get(user_id, {}).get("lang", "ru")

    try:
        day = int(message.text.strip())
        if not (1 <= day <= 31):
            raise ValueError
    except ValueError:
        texts = {
            "ru": "Введите корректное число месяца (1–31):",
            "uz": "To‘lov kunini to‘g‘ri kiriting (1–31):",
            "en": "Enter a valid day of the month (1–31):"
        }
        await message.answer(texts.get(lang, texts["ru"]))
        return

    user_data = data.get(user_id, {"subs": [], "lang": lang})
    if isinstance(user_data, list):
        user_data = {"subs": user_data, "lang": lang}
    subs = user_data["subs"]
    sub_data = await state.get_data()
    subs.append({
        "name": sub_data["name"],
        "price": sub_data["price"],
        "currency": sub_data["currency"],
        "day": day,
        "start": datetime.now().strftime("%Y-%m-%d"),
        "last_notified": None
    })
    user_data["subs"] = subs
    data[user_id] = user_data
    save_data(data)
    await state.clear()

    texts_added = {
        "ru": f"✅ Подписка добавлена!\n\n🎬 {sub_data['name']} — {sub_data['price']} {sub_data['currency']} / мес\n💳 Следующее списание: {day} числа\n\nℹ️ Уведомление придет за 24 часа до даты списания.",
        "uz": f"✅ Obuna qo‘shildi!\n\n🎬 {sub_data['name']} — {sub_data['price']} {sub_data['currency']} / oy\n💳 Keyingi to‘lov: {day}-kun\n\nℹ️ Xabarnoma to‘lovdan 24 soat oldin keladi.",
        "en": f"✅ Subscription added!\n\n🎬 {sub_data['name']} — {sub_data['price']} {sub_data['currency']} / month\n💳 Next payment: day {day}\n\nℹ️ Notification will arrive 24 hours before the payment date."
    }
    await message.answer(texts_added.get(lang, texts_added["ru"]),
                         reply_markup=get_after_add_keyboard(lang))

    # Если дата списания сегодня или завтра — уведомляем сразу
    now = datetime.now()
    today = now.day
    tomorrow = (now + timedelta(days=1)).day
    if day in [today, tomorrow]:
        texts_notify = {
            "ru": f"🔔 Напоминание!\nСкоро оплата подписки <b>{sub_data['name']}</b>.",
            "uz": f"🔔 Eslatma!\nTez orada <b>{sub_data['name']}</b> obunasi uchun to‘lov.",
            "en": f"🔔 Reminder!\nUpcoming payment for subscription <b>{sub_data['name']}</b>."
        }
        notify_text = texts_notify.get(lang, texts_notify["ru"])
        if day == today:
            day_text = {"ru": "\n💰 Оплата — <b>сегодня!</b>",
                        "uz": "\n💰 To‘lov — <b>bugun!</b>",
                        "en": "\n💰 Payment — <b>today!</b>"}
        else:
            day_text = {"ru": "\n📅 Оплата — <b>завтра!</b>",
                        "uz": "\n📅 To‘lov — <b>ertaga!</b>",
                        "en": "\n📅 Payment — <b>tomorrow!</b>"}
        notify_text += day_text.get(lang, day_text["ru"])
        await message.answer(notify_text, parse_mode="HTML")

        # фиксируем дату уведомления
        subs[-1]["last_notified"] = str(now.date())
        data[user_id] = user_data
        save_data(data)

# ============ /list ============
@dp.message(Command("list"))
async def list_subscriptions(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = str(message.from_user.id)
    data = load_data()
    lang = data.get(user_id, {}).get("lang", "ru")
    subs = data.get(user_id, {}).get("subs", [])

    no_subs_text = {
        "ru": "У вас пока нет подписок 💡",
        "uz": "Sizda hozircha obunalar yo‘q 💡",
        "en": "You have no subscriptions yet 💡"
    }

    if not subs:
        await message.answer(no_subs_text.get(lang, no_subs_text["ru"]))
        return

    list_text = {
        "ru": "📋 Ваши подписки:\n\n",
        "uz": "📋 Sizning obunalaringiz:\n\n",
        "en": "📋 Your subscriptions:\n\n"
    }
    text = list_text.get(lang, list_text["ru"])
    for i, s in enumerate(subs, start=1):
        if lang == "ru":
            text += f"{i}. {s.get('name')} — {s.get('price')} {s.get('currency')} — списание {s.get('day')} числа\n"
        elif lang == "uz":
            text += f"{i}. {s.get('name')} — {s.get('price')} {s.get('currency')} — to‘lov {s.get('day')} kuni\n"
        else:
            text += f"{i}. {s.get('name')} — {s.get('price')} {s.get('currency')} — payment on day {s.get('day')}\n"
    await message.answer(text)


import httpx

# Функция для получения актуального курса USD → UZS
async def fetch_usd_to_uzs():
    global USD_to_UZS
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("https://open.er-api.com/v6/latest/USD")
            data = response.json()
            USD_to_UZS = data["rates"]["UZS"]
    except Exception as e:
        print(f"Ошибка получения курса USD→UZS: {e}")
        USD_to_UZS = 11500  # запасной курс


# ============ /month ============
@dp.message(Command("month"))
async def month_expenses_start(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = str(message.from_user.id)
    data = load_data()
    lang = data.get(user_id, {}).get("lang", "ru")

    prompt_text = {
        "ru": "В какой валюте показать расходы? (USD или UZS)\n💡 Если выберете UZS для подписки в USD, сумма будет пересчитана по текущему курсу.",
        "uz": "Xarajatlarni qaysi valyutada ko‘rsatish? (USD yoki UZS)\n💡 Agar USDdagi obuna uchun UZSni tanlasangiz, summa joriy kurs bo‘yicha hisoblanadi.",
        "en": "In which currency to show expenses? (USD or UZS)\n💡 If you choose UZS for a subscription in USD, the amount will be converted at the current rate."
    }
    await message.answer(prompt_text.get(lang, prompt_text["ru"]))
    await state.set_state(MonthCurrency.waiting_for_currency)

@dp.message(MonthCurrency.waiting_for_currency)
async def month_expenses_calc(message: types.Message, state: FSMContext):
    currency_choice = message.text.strip().upper()
    if currency_choice not in ["USD", "UZS"]:
        # Сообщение на трех языках
        await message.answer("Введите только USD или UZS / Faqat USD yoki UZS kiriting / Enter only USD or UZS")
        return

    user_id = str(message.from_user.id)
    user_data = load_data().get(user_id, {})
    lang = user_data.get("lang", "ru")
    subs = user_data.get("subs", [])

    if not subs:
        no_subs_text = {
            "ru": "У вас нет активных подписок.",
            "uz": "Sizda faollashgan obunalar yo‘q.",
            "en": "You have no active subscriptions."
        }
        await message.answer(no_subs_text.get(lang, no_subs_text["ru"]))
        await state.clear()
        return

    # Получаем актуальный курс
    await fetch_usd_to_uzs()

    total = 0.0
    for s in subs:
        price = float(str(s.get("price", 0)).replace(" ", "").replace(",", "."))
        sub_currency = s.get("currency", "USD").upper()
        if sub_currency != currency_choice:
            if sub_currency == "USD" and currency_choice == "UZS":
                price *= USD_to_UZS
            elif sub_currency == "UZS" and currency_choice == "USD":
                price /= USD_to_UZS
        total += price

    total_text = {
        "ru": f"💰 Общие расходы за месяц: {total:.2f} {currency_choice}",
        "uz": f"💰 Oy davomida umumiy xarajatlar: {total:.2f} {currency_choice}",
        "en": f"💰 Total monthly expenses: {total:.2f} {currency_choice}"
    }
    await message.answer(total_text.get(lang, total_text["ru"]))
    await state.clear()



@dp.message(MonthCurrency.waiting_for_currency)
async def month_expenses_calc(message: types.Message, state: FSMContext):
    currency_choice = message.text.strip().upper()
    user_id = str(message.from_user.id)
    data = load_data()
    lang = data.get(user_id, {}).get("lang", "ru")
    if currency_choice not in ["USD", "UZS"]:
        invalid_text = {
            "ru": "Введите только USD или UZS:",
            "uz": "Faqat USD yoki UZS kiriting:",
            "en": "Enter only USD or UZS:"
        }
        await message.answer(invalid_text.get(lang, invalid_text["ru"]))
        return

    subs = data.get(user_id, {}).get("subs", [])
    if not subs:
        no_subs_text = {
            "ru": "У вас нет активных подписок.",
            "uz": "Sizda faollashtirilgan obunalar yo‘q.",
            "en": "You have no active subscriptions."
        }
        await message.answer(no_subs_text.get(lang, no_subs_text["ru"]))
        await state.clear()
        return

    total = 0.0
    for s in subs:
        price = float(str(s.get("price", 0)).replace(" ", "").replace(",", "."))
        sub_currency = s.get("currency", "USD").upper()
        if sub_currency != currency_choice:
            price = price * USD_to_UZS if sub_currency == "USD" else price / USD_to_UZS
        total += price

    total_text = {
        "ru": f"💰 Общие расходы за месяц: {total:.2f} {currency_choice}",
        "uz": f"💰 Oy bo‘yicha umumiy xarajatlar: {total:.2f} {currency_choice}",
        "en": f"💰 Total expenses for the month: {total:.2f} {currency_choice}"
    }
    await message.answer(total_text.get(lang, total_text["ru"]))
    await state.clear()


@dp.message(Command("soon"))
async def soon_subscriptions(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = str(message.from_user.id)
    data = load_data()
    lang = data.get(user_id, {}).get("lang", "ru")
    subs = data.get(user_id, {}).get("subs", [])

    no_subs_text = {
        "ru": "У вас нет подписок 💡",
        "uz": "Sizda obunalar yo‘q 💡",
        "en": "You have no subscriptions 💡"
    }

    if not subs:
        await message.answer(no_subs_text.get(lang, no_subs_text["ru"]))
        return

    now = datetime.now()
    soon_list = []
    for s in subs:
        try:
            day = int(s.get("day", 0))
        except ValueError:
            continue  # пропускаем, если день не число
        delta = day - now.day
        if 0 <= delta <= 7:
            soon_list.append((s.get("name"), day, delta))

    no_soon_text = {
        "ru": "📆 На этой неделе списаний нет.",
        "uz": "📆 Ushbu haftada to‘lovlar yo‘q.",
        "en": "📆 No payments this week."
    }

    if not soon_list:
        await message.answer(no_soon_text.get(lang, no_soon_text["ru"]))
        return

    header_text = {
        "ru": "📅 Ближайшие списания:\n",
        "uz": "📅 Yaqin to‘lovlar:\n",
        "en": "📅 Upcoming payments:\n"
    }

    text = header_text.get(lang, header_text["ru"])
    for name, day, delta in soon_list:
        if lang == "ru":
            if delta == 0:
                text += f"— {name}: сегодня\n"
            elif delta == 1:
                text += f"— {name}: завтра ({day} число)\n"
            else:
                text += f"— {name}: через {delta} дн. ({day} число)\n"
        elif lang == "uz":
            if delta == 0:
                text += f"— {name}: bugun\n"
            elif delta == 1:
                text += f"— {name}: ertaga ({day}-kun)\n"
            else:
                text += f"— {name}: {delta} kunda ({day}-kun)\n"
        else:  # en
            if delta == 0:
                text += f"— {name}: today\n"
            elif delta == 1:
                text += f"— {name}: tomorrow (day {day})\n"
            else:
                text += f"— {name}: in {delta} days (day {day})\n"

    await message.answer(text)


# ============ /cancel ============
@dp.message(Command("cancel"))
async def choose_cancel_subscription(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = str(message.from_user.id)
    data = load_data()
    lang = data.get(user_id, {}).get("lang", "ru")
    subs = data.get(user_id, {}).get("subs", [])
    valid_subs = [s for s in subs if isinstance(s, dict) and "name" in s]

    no_subs_text = {
        "ru": "У тебя пока нет подписок для отмены 😌",
        "uz": "Sizda bekor qilinadigan obunalar yo‘q 😌",
        "en": "You have no subscriptions to cancel 😌"
    }

    choose_text = {
        "ru": "Выбери подписку, которую хочешь отменить:",
        "uz": "Bekor qilmoqchi bo‘lgan obunani tanlang:",
        "en": "Choose a subscription to cancel:"
    }

    if not valid_subs:
        await message.answer(no_subs_text.get(lang, no_subs_text["ru"]))
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=sub["name"], callback_data=f"cancel_{sub['name']}")] for sub in valid_subs]
    )
    await message.answer(choose_text.get(lang, choose_text["ru"]), reply_markup=keyboard)


@dp.callback_query(lambda c: c.data.startswith("cancel_"))
async def process_cancel_callback(callback: types.CallbackQuery):
    await callback.answer()
    sub_name = callback.data.replace("cancel_", "")
    user_id = str(callback.from_user.id)
    data = load_data()
    lang = data.get(user_id, {}).get("lang", "ru")
    subs = data.get(user_id, {}).get("subs", [])

    sub_to_remove = next((s for s in subs if isinstance(s, dict) and s.get("name") == sub_name), None)

    not_found_text = {
        "ru": "Подписка не найдена 😅",
        "uz": "Obuna topilmadi 😅",
        "en": "Subscription not found 😅"
    }

    if not sub_to_remove:
        await callback.message.edit_text(not_found_text.get(lang, not_found_text["ru"]))
        return

    cancel_link = CANCEL_LINKS.get(sub_name)

    # Удаляем подписку
    subs = [s for s in subs if not (isinstance(s, dict) and s.get("name") == sub_name)]
    data[user_id]["subs"] = subs
    save_data(data)

    deleted_text = {
        "ru": f"Подписка '{sub_name}' удалена из списка ✅",
        "uz": f"'{sub_name}' obunasi ro‘yxatdan o‘chirildi ✅",
        "en": f"Subscription '{sub_name}' removed from the list ✅"
    }

    if cancel_link:
        link_text = {
            "ru": f"🔗 Ссылка для отмены {sub_name}:\n{cancel_link}\n\nПодписка удалена ✅",
            "uz": f"🔗 {sub_name} obunasini bekor qilish havolasi:\n{cancel_link}\n\nObuna o‘chirildi ✅",
            "en": f"🔗 Cancel link for {sub_name}:\n{cancel_link}\n\nSubscription removed ✅"
        }
        await callback.message.edit_text(link_text.get(lang, link_text["ru"]))
    else:
        await callback.message.edit_text(deleted_text.get(lang, deleted_text["ru"]))


# ============ Прерывание любых команд ============
@dp.message(F.text.regexp(r"^/"))
async def handle_any_command(message: types.Message, state: FSMContext):
    await state.clear()
    cmd = message.text.lower()
    if cmd.startswith("/add"):
        await add_subscription(message, state)
    elif cmd.startswith("/list"):
        await list_subscriptions(message, state)
    elif cmd.startswith("/month"):
        await month_expenses_start(message, state)
    elif cmd.startswith("/soon"):
        await soon_subscriptions(message, state)
    elif cmd.startswith(("/cancel", "/menu", "/start")):
        await start(message, state)
    else:
        await message.answer("Неизвестная команда 🤔 Попробуй /menu или /start")


async def check_subscriptions(bot):
    while True:
        data = load_data()
        now = datetime.now()
        today = now.day
        tomorrow = (now + timedelta(days=1)).day  # корректно для конца месяца

        for user_id, user_data in data.items():
            lang = user_data.get("lang", "ru")  # язык пользователя по умолчанию русский
            subs = user_data.get("subs", [])

            # Тексты уведомлений на трёх языках
            reminder_texts = {
                "reminder": {
                    "ru": "🔔 Напоминание!\nСкоро оплата подписки <b>{name}</b>.",
                    "uz": "🔔 Eslatma!\nObuna <b>{name}</b> bo‘yicha to‘lov yaqinlashmoqda.",
                    "en": "🔔 Reminder!\nPayment for subscription <b>{name}</b> is coming soon."
                },
                "today": {
                    "ru": "💰 Оплата — <b>сегодня!</b>",
                    "uz": "💰 To‘lov — <b>bugun!</b>",
                    "en": "💰 Payment — <b>today!</b>"
                },
                "tomorrow": {
                    "ru": "📅 Оплата — <b>завтра!</b>",
                    "uz": "📅 To‘lov — <b>ertaga!</b>",
                    "en": "📅 Payment — <b>tomorrow!</b>"
                }
            }

            for sub in subs:
                try:
                    day = int(sub.get("day", 0))
                except ValueError:
                    continue  # пропускаем, если день не число

                last_notified = sub.get("last_notified", "")  # дата последнего уведомления

                # Если сегодня или завтра и уведомления ещё не было
                if day in [today, tomorrow] and last_notified != str(now.date()):
                    text = reminder_texts["reminder"][lang].format(name=sub.get("name"))

                    if day == today:
                        text += "\n" + reminder_texts["today"][lang]
                    else:
                        text += "\n" + reminder_texts["tomorrow"][lang]

                    try:
                        await bot.send_message(int(user_id), text, parse_mode="HTML")
                    except Exception as e:
                        print(f"Ошибка отправки уведомления пользователю {user_id}: {e}")

                    # сохраняем дату уведомления, чтобы не дублировать
                    sub["last_notified"] = str(now.date())

                    if day == today:
                        print(f"Уведомление отправлено немедленно пользователю {user_id}")
                    else:
                        print(f"Уведомление о завтрашней подписке отправлено пользователю {user_id}")

            data[user_id]["subs"] = subs

        save_data(data)
        await asyncio.sleep(3600)  # проверка раз в час


# ====== ЗАПУСК ======
async def main():
    asyncio.create_task(check_subscriptions(bot))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())