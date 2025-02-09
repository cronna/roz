from flask import Flask, render_template, request, jsonify
import os
import requests
import asyncio
from models import Giveaway
from requests import get_giveaway_details, join_giveaway

app = Flask(__name__)
app.config['BOT_TOKEN'] = os.environ.get('BOT_TOKEN', '7790467084:AAGYK-Gm60ailV6B0q5K4bOgNaQ01oOu0L0')

def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

@app.route('/')
def index():
    start_param = request.args.get('start_param', '')
    giveaway_id = start_param.split('_')[1] if '_' in start_param else ''
    
    if not giveaway_id.isdigit():
        return render_template('error.html', message='Некорректный ID розыгрыша')
    
    # Получаем данные о розыгрыше
    giveaway = run_async(get_giveaway_details(int(giveaway_id)))
    
    if not giveaway:
        return render_template('error.html', message='Розыгрыш не найден')
    
    # Преобразуем объект Giveaway в словарь для передачи в шаблон
    giveaway_data = {
        'id': giveaway.id,
        'name': giveaway.name,
        'description': giveaway.description,
        'participants': giveaway.participants,
        'max_participants': giveaway.max_participants,
        'is_active': giveaway.is_active,
        'channels': [{'title': channel.title} for channel in giveaway.channels]
    }
    
    return render_template('index.html', giveaway=giveaway_data)

@app.route('/participate', methods=['POST'])
def handle_participation():
    data = request.json
    user_id = data.get('user_id')
    giveaway_id = data.get('giveaway_id')

    if not user_id or not giveaway_id:
        return jsonify({'status': 'error', 'message': 'Недостаточно данных'}), 400

    # Проверяем и добавляем участника
    try:
        success = run_async(join_giveaway(giveaway_id, user_id))
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

    if not success:
        return jsonify({
            'status': 'error',
            'message': 'Не удалось присоединиться к розыгрышу. Возможно, он завершен или достигнут лимит участников'
        }), 400

    # Отправляем сообщение через Telegram API
    bot_token = app.config['BOT_TOKEN']
    message = f"🎉 Вы успешно участвуете в розыгрыше!\nID розыгрыша: {giveaway_id}"
    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    try:
        response = requests.post(
            api_url,
            json={
                'chat_id': user_id,
                'text': message
            }
        )
        response.raise_for_status()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Ошибка отправки: {str(e)}'
        }), 500

if __name__ == '__main__':
    app.run(debug=True)