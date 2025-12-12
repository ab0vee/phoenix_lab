import os
import json
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

# Загрузка переменных окружения
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(BASE_DIR, '.env')
if not os.path.exists(env_path):
    env_path = os.path.join(BASE_DIR, 'BOT_TOKEN.env')
if os.path.exists(env_path):
    load_dotenv(env_path, override=True)
else:
    load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения")

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Файл для хранения каналов
CHANNELS_FILE = os.path.join(BASE_DIR, "TelegramBot", "channels.json")


def load_channels():
    """Загружает список каналов из файла"""
    if os.path.exists(CHANNELS_FILE):
        try:
            with open(CHANNELS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('channels', [])
        except Exception as e:
            logger.error(f"Ошибка загрузки каналов: {e}")
            return []
    return []


def save_channels(channels):
    """Сохраняет список каналов в файл"""
    try:
        with open(CHANNELS_FILE, 'w', encoding='utf-8') as f:
            json.dump({'channels': channels}, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения каналов: {e}")
        return False


def add_channel(channel_id, channel_name=None):
    """Добавляет канал в список"""
    channels = load_channels()
    channel_info = {
        'id': str(channel_id),
        'name': channel_name or str(channel_id)
    }
    
    # Проверяем, нет ли уже такого канала
    if any(ch['id'] == str(channel_id) for ch in channels):
        return False, "Канал уже добавлен"
    
    channels.append(channel_info)
    if save_channels(channels):
        return True, "Канал успешно добавлен"
    return False, "Ошибка сохранения"


def remove_channel(channel_id):
    """Удаляет канал из списка"""
    channels = load_channels()
    channels = [ch for ch in channels if ch['id'] != str(channel_id)]
    if save_channels(channels):
        return True, "Канал успешно удален"
    return False, "Ошибка сохранения"


# Состояния FSM
class ChannelManagement(StatesGroup):
    waiting_for_channel = State()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    await message.answer(
        "🔥 <b>Phoenix Lab</b> - Управление каналами\n\n"
        "Используйте команды:\n"
        "/channels - Список каналов\n"
        "/add_channel - Добавить канал\n"
        "/help - Помощь",
        parse_mode="HTML"
    )


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Помощь по командам"""
    await message.answer(
        "📋 <b>Доступные команды:</b>\n\n"
        "/start - Начать работу\n"
        "/channels - Показать список каналов\n"
        "/add_channel - Добавить новый канал\n"
        "/cancel - Отменить текущую операцию\n\n"
        "<b>Как добавить канал:</b>\n"
        "1. Добавьте бота в канал как администратора\n"
        "2. Используйте /add_channel\n"
        "3. Перешлите сообщение из канала",
        parse_mode="HTML"
    )


@dp.message(Command("channels"))
async def cmd_channels(message: types.Message):
    """Показывает список каналов для рассылки"""
    channels = load_channels()
    
    if not channels:
        await message.answer(
            "❌ Каналы не настроены.\n\n"
            "Используйте команду /add_channel для добавления канала."
        )
        return
    
    # Создаем клавиатуру с кнопками удаления
    keyboard_buttons = []
    channels_text = "📢 <b>Каналы для рассылки:</b>\n\n"
    
    for i, channel in enumerate(channels):
        channels_text += f"{i+1}. {channel['name']} (<code>{channel['id']}</code>)\n"
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"❌ Удалить {channel['name']}",
                callback_data=f"remove_channel_{channel['id']}"
            )
        ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await message.answer(
        channels_text,
        parse_mode="HTML",
        reply_markup=keyboard
    )


@dp.message(Command("add_channel"))
async def cmd_add_channel(message: types.Message, state: FSMContext):
    """Начинает процесс добавления канала"""
    await message.answer(
        "📝 <b>Добавление канала:</b>\n\n"
        "1. Перешлите сообщение из канала, куда добавлен бот\n"
        "2. Или отправьте ID канала (например: -1001234567890)\n\n"
        "Используйте /cancel для отмены.",
        parse_mode="HTML"
    )
    await state.set_state(ChannelManagement.waiting_for_channel)


@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    """Отменяет текущую операцию"""
    await state.clear()
    await message.answer("❌ Операция отменена.")


@dp.message(ChannelManagement.waiting_for_channel)
async def process_channel(message: types.Message, state: FSMContext):
    """Обрабатывает добавление канала"""
    channel_id = None
    channel_name = None
    
    # Если это пересланное сообщение из канала
    if message.forward_from_chat:
        channel_id = str(message.forward_from_chat.id)
        channel_name = message.forward_from_chat.title or message.forward_from_chat.username or channel_id
    # Если это просто текст с ID
    elif message.text:
        text = message.text.strip()
        # Проверяем, похоже ли на ID канала (начинается с -100)
        if text.startswith('-100') and text[1:].replace('-', '').isdigit():
            channel_id = text
            channel_name = text
        else:
            await message.answer(
                "❌ Неверный формат ID канала.\n"
                "ID канала должен начинаться с -100 и содержать только цифры.\n"
                "Пример: -1001234567890\n\n"
                "Или перешлите сообщение из канала."
            )
            return
    
    if not channel_id:
        await message.answer("❌ Не удалось определить канал. Попробуйте ещё раз.")
        return
    
    # Пытаемся получить информацию о канале
    try:
        chat = await bot.get_chat(channel_id)
        channel_name = chat.title or chat.username or channel_id
    except Exception as e:
        logger.warning(f"Не удалось получить информацию о канале {channel_id}: {e}")
        await message.answer(
            "⚠️ Не удалось получить информацию о канале.\n"
            "Убедитесь, что бот добавлен в канал как администратор."
        )
    
    # Добавляем канал
    success, msg = add_channel(channel_id, channel_name)
    
    if success:
        await message.answer(
            f"✅ {msg}\n\n"
            f"📢 Канал: {channel_name}\n"
            f"🆔 ID: <code>{channel_id}</code>",
            parse_mode="HTML"
        )
    else:
        await message.answer(f"❌ {msg}")
    
    await state.clear()


@dp.callback_query(lambda c: c.data.startswith("remove_channel_"))
async def remove_channel_callback(callback: types.CallbackQuery):
    """Удаляет канал по callback"""
    channel_id = callback.data.replace("remove_channel_", "")
    
    channels = load_channels()
    channel_name = next((ch['name'] for ch in channels if ch['id'] == channel_id), channel_id)
    
    success, msg = remove_channel(channel_id)
    
    if success:
        await callback.answer(f"Канал {channel_name} удален")
        await callback.message.edit_text(
            f"✅ Канал <b>{channel_name}</b> удален из списка.",
            parse_mode="HTML"
        )
    else:
        await callback.answer(f"Ошибка: {msg}")


@dp.message()
async def handle_other_messages(message: types.Message, state: FSMContext):
    """Обработка прочих сообщений"""
    current_state = await state.get_state()
    if current_state == ChannelManagement.waiting_for_channel:
        await process_channel(message, state)
    else:
        await message.answer(
            "👋 Используйте команды:\n"
            "/start - Начать работу\n"
            "/channels - Список каналов\n"
            "/add_channel - Добавить канал\n"
            "/help - Помощь\n"
            "/cancel - Отменить операцию"
        )


async def main():
    """Запуск бота"""
    logger.info("Бот запущен")
    channels = load_channels()
    logger.info(f"Настроено каналов: {len(channels)}")
    if channels:
        logger.info(f"Каналы: {', '.join([ch['name'] for ch in channels])}")
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

