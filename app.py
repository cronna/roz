from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

import os

from uvicorn import run

import httpx

import asyncio
from requests import get_giveaway_details, join_giveaway

app = FastAPI()
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8194187894:AAGmqMe6Nw0oZn9f77UpciKR4qf8GatZZ1w')

templates = Jinja2Templates(directory="templates")


def run_async(coro):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    except Exception as e:
        print(f"Ошибка в run_async: {e}")
        return None
    finally:
        loop.close()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, start_param: str = ''):
    giveaway_id = start_param.split('_')[1] if '_' in start_param and start_param.split('_')[1].isdigit() else None

    if not giveaway_id:
        return templates.TemplateResponse("error.html", {"request": request, "message": "Некорректный ID розыгрыша"})
    giveaway = run_async(get_giveaway_details(int(giveaway_id)))

    if not giveaway:
        return templates.TemplateResponse("error.html", {"request": request, "message": "Розыгрыш не найден"})
    giveaway_data = {
        'id': giveaway.id,
        'name': giveaway.name,
        'description': giveaway.description,
        'participants': giveaway.participants,
        'max_participants': giveaway.max_participants,
        'is_active': giveaway.is_active,
        'channels': [{'title': channel.title} for channel in getattr(giveaway, 'channels', [])]
    }

    return templates.TemplateResponse("index.html", {"request": request, "giveaway": giveaway_data})


@app.post("/participate")
async def handle_participation(request: Request):
    data = await request.json()
    user_id = data.get('user_id')
    giveaway_id = data.get('giveaway_id')

    if not user_id or not giveaway_id:
        raise HTTPException(status_code=400, detail='Недостаточно данных')
    try:
        success = await join_giveaway(giveaway_id, user_id)
        if not success:
            raise HTTPException(status_code=400, detail='Не удалось присоединиться к розыгрышу')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Ошибка обработки: {str(e)}')

    if not BOT_TOKEN:
        raise HTTPException(status_code=500, detail='Отсутствует токен бота')

    message = f"🎉 Вы успешно участвуете в розыгрыше!\nID розыгрыша: {giveaway_id}"

    async with httpx.AsyncClient() as client:
        api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        try:
            response = await client.post(api_url, json={'chat_id': user_id, 'text': message})
            response.raise_for_status()
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f'Ошибка отправки: {str(e)}')

    return JSONResponse(content={'status': 'success'})


run(app)
