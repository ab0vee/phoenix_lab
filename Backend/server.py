from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import logging
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)  # Разрешаем CORS для запросов с сайта

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения")

# Определяем путь к файлу каналов относительно корня проекта
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHANNELS_FILE = os.path.join(BASE_DIR, "TelegramBot", "channels.json")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


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
        
        # Отправляем статью во все выбранные каналы
        for channel in channels_to_send:
            try:
                url = f"{TELEGRAM_API_URL}/sendMessage"
                payload = {
                    'chat_id': channel['id'],
                    'text': article_text,
                    'parse_mode': 'HTML'
                }
                
                response = requests.post(url, json=payload, timeout=10)
                
                if response.status_code == 200:
                    success_count += 1
                    logger.info(f"Статья отправлена в канал: {channel['name']} ({channel['id']})")
                else:
                    error_msg = response.json().get('description', 'Unknown error')
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

