from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import logging
import asyncio
import re
import requests
from bs4 import BeautifulSoup
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from dotenv import load_dotenv

# Загружаем .env из корня проекта или из папки Backend
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(BASE_DIR, '.env')
if not os.path.exists(env_path):
    env_path = os.path.join(BASE_DIR, 'BOT_TOKEN.env')
    # Если файл BOT_TOKEN.env существует, загружаем его
    if os.path.exists(env_path):
        load_dotenv(env_path, override=True)
    else:
        load_dotenv()
else:
    load_dotenv(env_path)

# Загружаем groq.env если существует
groq_env_path = os.path.join(BASE_DIR, 'Backend', 'groq.env')
if os.path.exists(groq_env_path):
    load_dotenv(groq_env_path, override=True)

app = Flask(__name__)
CORS(app)  # Разрешаем CORS для запросов с сайта

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаём папку TelegramBot если её нет
TELEGRAM_BOT_DIR = os.path.join(BASE_DIR, "TelegramBot")
if not os.path.exists(TELEGRAM_BOT_DIR):
    os.makedirs(TELEGRAM_BOT_DIR)
    logger.info(f"Создана папка: {TELEGRAM_BOT_DIR}")

CHANNELS_FILE = os.path.join(TELEGRAM_BOT_DIR, "channels.json")

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    logger.error(f"BOT_TOKEN не найден. Проверьте файл: {env_path}")
    raise ValueError("BOT_TOKEN не найден в переменных окружения")

# Groq API настройки
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.1-70b-versatile')  # По умолчанию используем Llama 3.1

logger.info("BOT_TOKEN успешно загружен")
logger.info(f"Используется файл каналов: {CHANNELS_FILE}")
if GROQ_API_KEY:
    logger.info("Groq API настроен")
    logger.info(f"Groq модель: {GROQ_MODEL}")
else:
    logger.warning("Groq API не настроен. Добавьте GROQ_API_KEY в .env")

# Bot будет создаваться для каждого запроса, чтобы избежать проблем с сессией
logger.info("Aiogram Bot готов к использованию")


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


def clean_model_response(text):
    """Очищает ответ модели от мыслей, комментариев и лишних фраз"""
    if not text:
        return ""
    
    original_text = text
    text = text.strip()
    
    # Удаляем теги reasoning (включая содержимое между ними)
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<reasoning>.*?</reasoning>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL | re.IGNORECASE)
    # Удаляем оставшиеся одиночные теги
    text = re.sub(r'</?redacted_reasoning>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'</?reasoning>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'</?thinking>', '', text, flags=re.IGNORECASE)
    
    # Удаляем распространённые предисловия (регистронезависимо)
    prefixes_to_remove = [
        r"^вот переписанный текст:?\s*",
        r"^переписанный текст:?\s*",
        r"^вот вариант:?\s*",
        r"^вот переписанный вариант:?\s*",
        r"^переписанный вариант:?\s*",
        r"^вот текст:?\s*",
        r"^текст в стиле:?\s*",
        r"^думаю:?\s*",
        r"^я думаю:?\s*",
        r"^можно переписать так:?\s*",
        r"^переписанный вариант текста:?\s*",
        r"^вот как можно переписать:?\s*",
        r"^вот переписанный:?\s*",
        r"^переписанный:?\s*",
        r"^вот:?\s*",
        r"^think:?\s*",
        r"^thinking:?\s*",
        r"^я думаю,?\s*",
        r"^думаю,?\s*",
    ]
    
    for prefix in prefixes_to_remove:
        text = re.sub(prefix, '', text, flags=re.IGNORECASE).strip()
    
    # Удаляем мысли в скобках
    text = re.sub(r'\([^)]*(?:думаю|я думаю|можно|вариант|переписанный|think|thinking)[^)]*\)', '', text, flags=re.IGNORECASE)
    
    # Удаляем кавычки в начале и конце, если они есть
    text = re.sub(r'^["\'«»]|["\'«»]$', '', text).strip()
    
    # Удаляем строки, которые выглядят как мысли
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Пропускаем строки, которые явно являются мыслями
        thought_patterns = [
            r'^(думаю|я думаю|можно|вариант|переписанный|вот|это|так|например|то есть|think|thinking)',
            r'^\(.*(думаю|можно|вариант).*\)$'
        ]
        
        is_thought = False
        for pattern in thought_patterns:
            if re.match(pattern, line, re.IGNORECASE) and len(line) < 150:
                is_thought = True
                break
        
        if not is_thought:
            cleaned_lines.append(line)
    
    result = '\n'.join(cleaned_lines).strip()
    
    # Если после очистки осталось слишком мало текста, возвращаем оригинал
    if len(result) < 20:
        return original_text.strip()
    
    return result


def extract_article_text(url):
    """Извлекает текст статьи из URL"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        response.encoding = response.apparent_encoding or 'utf-8'
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Удаляем скрипты и стили
        for script in soup(["script", "style", "nav", "header", "footer"]):
            script.decompose()
        
        # Пытаемся найти основной контент статьи
        # Для Dzen.ru и других платформ
        article = (soup.find('article') or 
                  soup.find('main') or 
                  soup.find('div', class_='content') or
                  soup.find('div', class_='article') or
                  soup.find('div', {'data-testid': 'article-content'}) or
                  soup.find('div', class_='zen-article') or
                  soup.find('div', class_='article-body'))
        
        if article:
            text = article.get_text(separator='\n', strip=True)
        else:
            # Если не нашли, берём весь body, но удаляем навигацию и футеры
            body = soup.find('body')
            if body:
                text = body.get_text(separator='\n', strip=True)
            else:
                text = soup.get_text(separator='\n', strip=True)
        
        # Очищаем текст от лишних пробелов и пустых строк
        lines = [line.strip() for line in text.split('\n') if line.strip() and len(line.strip()) > 3]
        cleaned_text = '\n'.join(lines)
        
        if not cleaned_text or len(cleaned_text) < 50:
            raise ValueError(f"Извлечённый текст слишком короткий или пуст ({len(cleaned_text) if cleaned_text else 0} символов)")
        
        return cleaned_text
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка HTTP запроса к {url}: {e}")
        raise ValueError(f"Не удалось загрузить страницу: {str(e)}")
    except Exception as e:
        logger.error(f"Ошибка извлечения текста из {url}: {e}")
        raise


def rewrite_article_with_groq(article_text, style):
    """Рерайтит статью через Groq API"""
    if not GROQ_API_KEY:
        raise ValueError("Groq API не настроен. Добавьте GROQ_API_KEY в .env")
    
    # Маппинг стилей для промпта
    style_mapping = {
        'scientific': 'НАУЧНО-ДЕЛОВОЙ',
        'meme': 'МЕМНЫЙ',
        'casual': 'ПОВСЕДНЕВНЫЙ'
    }
    
    style_name = style_mapping.get(style, 'ПОВСЕДНЕВНЫЙ')
    
    # Ограничиваем длину текста (Groq имеет лимиты)
    max_text_length = 12000
    if len(article_text) > max_text_length:
        article_text = article_text[:max_text_length] + "..."
    
    # Формируем промпт пользователя
    full_prompt = f"Перепиши следующий текст в стиле {style_name}:\n\n{article_text}"
    
    try:
        headers = {
            'Authorization': f'Bearer {GROQ_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": """Ты — инструмент для рерайта текстов. Твоя единственная задача — переписать предоставленный текст в указанном стиле БЕЗ МЫСЛЕЙ.

Доступные стили:
- НАУЧНО-ДЕЛОВОЙ: формально, объективно, научная терминология
- МЕМНЫЙ: интернет-мемы, эмодзи, сленг, сарказм
- ПОВСЕДНЕВНЫЙ: просто, естественно, разговорно

ПРАВИЛА:
1. Отвечай ТОЛЬКО переписанным текстом
2. НИКАКИХ объяснений, комментариев, предисловий
3. НИКАКИХ фраз типа "Вот текст:", "Переписанный вариант:", "Думаю:" и т.п.
4. НИКАКИХ мыслей, рассуждений, мета-комментариев
5. НИКАКИХ кавычек вокруг текста
6. Начинай сразу с переписанного текста
7. Сохраняй смысл оригинала
8. Длина примерно как у оригинала"""
                },
                {
                    "role": "user",
                    "content": full_prompt
                }
            ],
            "temperature": 0.5,  # Снижено для более детерминированного поведения
            "max_tokens": 4000,
            "top_p": 0.95,
            "stream": False,
            # Параметр для скрытия размышлений модели (если модель поддерживает)
            "reasoning_format": "hidden" if "deepseek" in GROQ_MODEL.lower() or "r1" in GROQ_MODEL.lower() else None,
            # Стоп-последовательности для остановки генерации при начале мыслей (максимум 4 элемента)
            "stop": [
                "\nДумаю:",
                "\nВот переписанный текст:",
                "\nThink:",
                "\n("
            ]
        }
        
        # Удаляем None значения из payload
        payload = {k: v for k, v in payload.items() if v is not None}
        
        logger.info(f"Отправка запроса в Groq для стиля: {style}")
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        logger.info(f"Ответ Groq получен")
        
        # Обрабатываем ответ Groq API
        if 'choices' in result and len(result['choices']) > 0:
            rewritten_text = result['choices'][0]['message']['content']
            
            # Очищаем ответ от мыслей модели и лишних комментариев
            cleaned_text = clean_model_response(rewritten_text)
            return cleaned_text
        else:
            logger.error(f"Неожиданный формат ответа: {result}")
            raise ValueError("Неожиданный формат ответа от Groq API")
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка HTTP запроса к Groq: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                logger.error(f"Ответ сервера: {error_detail}")
            except:
                logger.error(f"Ответ сервера: {e.response.text}")
        raise ValueError(f"Ошибка подключения к Groq API: {str(e)}")
    except Exception as e:
        logger.error(f"Ошибка рерайта через Groq: {e}")
        raise


@app.route('/api/rewrite-article', methods=['POST'])
def rewrite_article():
    """Рерайтит статью через Groq API"""
    try:
        if not request.json:
            return jsonify({'success': False, 'error': 'Отсутствует тело запроса'}), 400
        
        data = request.json
        article_url = data.get('url', '')
        style = data.get('style', 'casual')
        
        if not article_url:
            logger.error("URL статьи не указан в запросе")
            return jsonify({'success': False, 'error': 'URL статьи не указан'}), 400
        
        if style not in ['scientific', 'meme', 'casual']:
            logger.error(f"Неверный стиль рерайта: {style}")
            return jsonify({'success': False, 'error': 'Неверный стиль рерайта'}), 400
        
        # Извлекаем текст статьи
        logger.info(f"Извлечение текста из URL: {article_url}")
        try:
            article_text = extract_article_text(article_url)
            logger.info(f"Текст извлечён, длина: {len(article_text)} символов")
        except Exception as e:
            logger.error(f"Ошибка извлечения текста из {article_url}: {e}")
            return jsonify({'success': False, 'error': f'Не удалось извлечь текст статьи: {str(e)}'}), 400
        
        if not article_text:
            logger.error("Извлечённый текст пуст")
            return jsonify({'success': False, 'error': 'Не удалось извлечь текст статьи'}), 400
        
        if len(article_text) < 50:
            logger.warning(f"Текст слишком короткий: {len(article_text)} символов")
            return jsonify({'success': False, 'error': f'Текст статьи слишком короткий ({len(article_text)} символов). Минимум 50 символов.'}), 400
        
        # Рерайтим через Groq
        logger.info(f"Рерайт статьи в стиле: {style}, длина текста: {len(article_text)}")
        try:
            rewritten_text = rewrite_article_with_groq(article_text, style)
            logger.info(f"Рерайт завершён, длина результата: {len(rewritten_text)} символов")
        except Exception as e:
            logger.error(f"Ошибка рерайта через Groq: {e}")
            return jsonify({'success': False, 'error': f'Ошибка рерайта: {str(e)}'}), 500
        
        return jsonify({
            'success': True,
            'text': rewritten_text
        }), 200
        
    except ValueError as e:
        logger.error(f"Ошибка валидации: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Неожиданная ошибка рерайта статьи: {e}", exc_info=True)
        return jsonify({'success': False, 'error': f'Внутренняя ошибка сервера: {str(e)}'}), 500


@app.route('/api/send-article', methods=['POST'])
def send_article():
    """Отправляет статью в каналы через Telegram Bot API"""
    try:
        data = request.json
        article_text = data.get('article_text', '')
        selected_channels = data.get('channels', [])  # Список ID каналов для отправки
        
        if not article_text.strip():
            return jsonify({'success': False, 'error': 'Текст статьи не может быть пустым'}), 400
        
        # Загружаем каналы
        all_channels = load_channels()
        
        # Если указаны конкретные каналы, используем их, иначе все
        if selected_channels:
            channels_to_send = [ch for ch in all_channels if ch['id'] in selected_channels]
        else:
            channels_to_send = all_channels
        
        if not channels_to_send:
            return jsonify({'success': False, 'error': 'Каналы не настроены'}), 400
        
        success_count = 0
        failed_channels = []
        
        # Асинхронная функция для отправки сообщений
        async def send_messages():
            nonlocal success_count, failed_channels
            # Создаём новый экземпляр Bot для этого запроса
            current_bot = Bot(token=BOT_TOKEN)
            try:
                for channel in channels_to_send:
                    try:
                        await current_bot.send_message(
                            chat_id=channel['id'],
                            text=article_text,
                            parse_mode='HTML'
                        )
                        success_count += 1
                        logger.info(f"Статья отправлена в канал: {channel['name']} ({channel['id']})")
                    except TelegramAPIError as e:
                        error_msg = str(e)
                        failed_channels.append({
                            'channel': channel['name'],
                            'error': error_msg
                        })
                        logger.error(f"Ошибка отправки в канал {channel['name']}: {error_msg}")
                    except Exception as e:
                        failed_channels.append({
                            'channel': channel.get('name', channel['id']),
                            'error': str(e)
                        })
                        logger.error(f"Ошибка отправки в канал {channel['id']}: {e}")
            finally:
                # Закрываем сессию бота после отправки
                await current_bot.session.close()
        
        # Запускаем асинхронную функцию
        # Всегда создаём новый event loop для каждого запроса
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(send_messages())
        except Exception as e:
            logger.error(f"Ошибка работы с event loop: {e}")
            raise
        finally:
            # Закрываем loop после использования
            try:
                # Отменяем все незавершённые задачи
                pending = [t for t in asyncio.all_tasks(loop) if not t.done()]
                for task in pending:
                    task.cancel()
                # Ждём отмены задач
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except Exception:
                pass
            finally:
                if not loop.is_closed():
                    loop.close()
        
        return jsonify({
            'success': True,
            'sent': success_count,
            'total': len(channels_to_send),
            'failed': failed_channels
        }), 200
        
    except Exception as e:
        logger.error(f"Ошибка обработки запроса: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/channels', methods=['GET'])
def get_channels():
    """Возвращает список доступных каналов"""
    try:
        channels = load_channels()
        return jsonify({
            'success': True,
            'channels': channels
        }), 200
    except Exception as e:
        logger.error(f"Ошибка получения каналов: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health():
    """Проверка работоспособности сервера"""
    return jsonify({'status': 'ok'}), 200


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

