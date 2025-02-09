from flask import Flask, render_template, request, jsonify
import os
import requests

app = Flask(__name__)
app.config['BOT_TOKEN'] = os.environ.get('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')

@app.route('/')
def index():
    start_param = request.args.get('start_param', '')
    giveaway_id = start_param.split('_')[1] if '_' in start_param else ''
    return render_template('index.html', giveaway_id=giveaway_id)

@app.route('/participate', methods=['POST'])
def handle_participation():
    data = request.json
    user_id = data.get('user_id')
    giveaway_id = data.get('giveaway_id')

    if not user_id or not giveaway_id:
        return jsonify({'status': 'error', 'message': 'Недостаточно данных'}), 400

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