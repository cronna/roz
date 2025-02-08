import logging, asyncio
from aiogram.types import WebAppInfo
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder
from models import async_main
from requests import *
from keyboards import *
import json

logging.basicConfig(level=logging.INFO)

API_TOKEN = '7790467084:AAGYK-Gm60ailV6B0q5K4bOgNaQ01oOu0L0'
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

class GiveawayStates(StatesGroup):
    name = State()
    description = State()
    max_participants = State()
    add_channels = State()
    select_winner = State() 

from aiogram.types import WebAppInfo

# Добавим новый обработчик для команды start с параметром giveaway
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
import logging
import hashlib
import hmac
import json

# Конфигурация
API_TOKEN = API_TOKEN
WEBAPP_URL = "https://cronna.github.io/roz_html/giveaway.html"  # URL вашего мини-приложения

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Команда /start с передачей параметра розыгрыша
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("giveaway_"):
        giveaway_id = args[1].split("=")[1]
        await message.answer(
            "Нажмите кнопку, чтобы участвовать в розыгрыше:",
            reply_markup=InlineKeyboardBuilder().button(
                text="Участвовать",
                web_app=WebAppInfo(url=f"{WEBAPP_URL}?giveaway_id={giveaway_id}")
            ).as_markup()
        )
    else:
        await message.answer("Используйте ссылку с параметром розыгрыша.")


@dp.message(F.text == "Создать розыгрыш")
async def process_create_giveaway(message: Message, state: FSMContext):
    await message.answer("Введите название розыгрыша:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(GiveawayStates.name)

@dp.message(GiveawayStates.name)
async def process_name(message: Message, state: FSMContext):
    if message.text == "Отменить":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu())
        return
    await state.update_data(name=message.text)
    await message.answer("Введите описание розыгрыша:")
    await state.set_state(GiveawayStates.description)

@dp.message(GiveawayStates.description)
async def process_description(message: Message, state: FSMContext):
    if message.text == "Отменить":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu())
        return
    await state.update_data(description=message.text)
    await message.answer("Введите максимальное количество участников:")
    await state.set_state(GiveawayStates.max_participants)

@dp.message(GiveawayStates.max_participants)
async def process_max_participants(message: Message, state: FSMContext):
    if message.text == "Отменить":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu())
        return
    try:
        max_participants = int(message.text)
        if max_participants <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Введите корректное положительное число!")
        return
    
    await state.update_data(max_participants=max_participants)
    await message.answer("Теперь добавьте каналы для розыгрыша (до 10).", reply_markup=add_channel_kb)

@dp.callback_query(F.data == 'add_channel')
async def add_channel_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer('Добавьте бота в канал в роли админа и перешлите сообщение из канала:')
    await state.set_state(GiveawayStates.add_channels)

@dp.message(GiveawayStates.add_channels)
async def process_add_channels(message: Message, state: FSMContext):
    global bot
    if message.text == "Отменить":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu())
        return
    
    if not message.forward_from_chat or message.forward_from_chat.type != 'channel':
        await message.answer("Перешлите сообщение из канала!")
        return
    
    try:
        chat_member = await bot.get_chat_member(message.forward_from_chat.id, bot.id)
        if chat_member.status not in ['administrator', 'creator']:
            await message.answer("Бот не является администратором этого канала. Добавьте его и попробуйте снова.")
            return
    except Exception as e:
        logging.error(f"Ошибка проверки прав бота: {e}")
        await message.answer("Не удалось проверить права бота в канале. Убедитесь, что бот добавлен как администратор.")
        return
    
    data = await state.get_data()
    giveaway_id = data.get('giveaway_id')
    user_id = message.from_user.id
    
    if not giveaway_id:
        giveaway_data = {
            'name': data['name'],
            'description': data['description'],
            'max_participants': data['max_participants'],
            'creator_id': user_id
        }
        giveaway_id = await create_giveaway(**giveaway_data)
        await state.update_data(giveaway_id=giveaway_id)
    
    channel_id = await create_channel(
        tg_id=message.forward_from_chat.id,
        title=message.forward_from_chat.title,
        invite_link=f"https://t.me/{message.forward_from_chat.username}" if message.forward_from_chat.username else await bot.export_chat_invite_link(message.forward_from_chat.id),
        creator_id=user_id
    )
    
    success = await add_channel_to_giveaway(giveaway_id, channel_id)
    if not success:
        await message.answer("Не удалось добавить канал. Попробуйте еще раз.")
        return
    
    channels = await get_giveaway_channels(giveaway_id)
    channels_count = len(channels)
    
    if channels_count >= 10:
        await message.answer("Достигнут лимит каналов (10). Розыгрыш создан!", reply_markup=main_menu())
        await state.clear()
    else:
        builder = InlineKeyboardBuilder()
        builder.button(text="Добавить еще канал", callback_data='add_channel')
        builder.button(text="Готово", callback_data='finish_add_channels')
        builder.adjust(1, repeat=True)
        await message.answer(
            f"Канал добавлен. Добавлено каналов: {channels_count}/10.",
            reply_markup=builder.as_markup()
        )

@dp.callback_query(F.data == "finish_add_channels")
async def finish_add_channels(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    giveaway_id = data['giveaway_id']
    
    deep_link = await generate_giveaway_link(giveaway_id)
    
    async with async_session() as session:
        giveaway = await session.get(Giveaway, giveaway_id)
        giveaway.deep_link = deep_link
        await session.commit()
    
    await callback.message.answer(
        f"✅ Розыгрыш создан!\n\n"
        f"🔗 Ссылка для участия:\n{deep_link}",
        reply_markup=main_menu()
    )
    await state.clear()

@dp.message(F.web_app_data)
async def handle_web_app_data(message: Message):
    try:
        data = json.loads(message.web_app_data.data)
        giveaway_id = data.get('giveaway_id')
        user_id = message.from_user.id
        
        giveaway = await get_giveaway_details(giveaway_id)
        if not giveaway or not giveaway.is_active:
            await message.answer("🚫 Розыгрыш завершен или не найден")
            return
        
        # Проверка подписок
        channel_ids = [channel.tg_id for channel in giveaway.channels]
        if channel_ids:
            is_subscribed = await check_user_subscription(user_id, channel_ids, bot)
            if not is_subscribed:
                await message.answer(
                    "📢 Для участия необходимо подписаться на каналы:",
                    reply_markup=await channels_subscription_keyboard(giveaway_id)
                )
                return
        
        # Добавление участника
        success = await join_giveaway(giveaway_id, user_id)
        if success:
            await message.answer(
                f"🎉 Вы участвуете в розыгрыше!\n\n"
                f"Название: {giveaway.name}\n"
                f"Описание: {giveaway.description}\n"
                f"Участников: {giveaway.participants}/{giveaway.max_participants}",
                reply_markup=giveaway_details_keyboard(giveaway_id)
            )
        else:
            await message.answer("❌ Не удалось присоединиться. Лимит участников достигнут.")
            
    except Exception as e:
        logging.error(f"Web app error: {e}")
        await message.answer("⚠️ Произошла ошибка при обработке запроса")

@dp.message(F.text == "Мои розыгрыши")
async def show_my_giveaways(message: Message):
    giveaways = await get_all_give()
    if not giveaways:
        await message.answer("У вас пока нет активных розыгрышей.")
        return
    
    await message.answer("Ваши розыгрыши:", reply_markup=await pagination_keyboard(1))

@dp.callback_query(F.data.startswith('page_'))
async def to_right(callback: CallbackQuery):
    await callback.answer()
    page = int(callback.data.split('_')[1])
    await callback.message.edit_reply_markup(reply_markup=await pagination_keyboard(page))

@dp.callback_query(lambda c: c.data.startswith('giveaway_'))
async def process_giveaway(callback: CallbackQuery):
    giveaway_id = int(callback.data.split('_')[1])
    giveaway = await get_giveaway_details(giveaway_id)
    
    if not giveaway:
        await callback.answer("Розыгрыш не найден.")
        return
    
    text = (
        f"🎉 Розыгрыш: {giveaway.name}\n"
        f"📝 Описание: {giveaway.description}\n"
        f"👥 Участники: {giveaway.participants}/{giveaway.max_participants}\n"
        f"🆔 ID: {giveaway.id}"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=giveaway_details_keyboard(giveaway.id)
    )

@dp.callback_query(F.data.startswith('join_'))
async def join_giveaway_handler(callback: CallbackQuery):
    giveaway_id = int(callback.data.split('_')[1])
    user_id = callback.from_user.id
    
    giveaway = await get_giveaway_details(giveaway_id)
    if not giveaway:
        await callback.answer("Розыгрыш не найден.")
        return
    
    channel_ids = [channel.tg_id for channel in giveaway.channels]
    if not channel_ids:
        # Если каналов нет, сразу добавляем участника
        success = await join_giveaway(giveaway_id, user_id)
        if success:
            await callback.answer("Вы успешно присоединились к розыгрышу!")
        else:
            await callback.answer("Не удалось присоединиться. Возможно, розыгрыш завершен или достигнут лимит участников.")
        return
    
    # Создаем клавиатуру с каналами
    channels_kb = await channels_subscription_keyboard(giveaway_id)
    
    await callback.message.edit_text(
        "Для участия в розыгрыше необходимо подписаться на следующие каналы:",
        reply_markup=channels_kb
    )

@dp.callback_query(F.data.startswith('check_subscription_'))
async def check_subscription_handler(callback: CallbackQuery):
    giveaway_id = int(callback.data.split('_')[2])
    user_id = callback.from_user.id
    
    giveaway = await get_giveaway_details(giveaway_id)
    if not giveaway:
        await callback.answer("Розыгрыш не найден.")
        return
    
    channel_ids = [channel.tg_id for channel in giveaway.channels]
    if not channel_ids:
        await callback.answer("Ошибка: нет каналов для подписки.")
        return
    
    is_subscribed = await check_user_subscription(user_id, channel_ids, bot)
    if is_subscribed:
        success = await join_giveaway(giveaway_id, user_id)
        if success:
            await callback.message.edit_text(
                "✅ Вы успешно присоединились к розыгрышу!",
                reply_markup=giveaway_details_keyboard(giveaway_id)
            )
        else:
            await callback.answer("Не удалось присоединиться. Возможно, розыгрыш завершен или достигнут лимит участников.")
    else:
        await callback.answer("Вы все еще не подписаны на все каналы!")



 # Новое состояние для выбора победителя

@dp.callback_query(F.data.startswith('manage_giveaway_'))
async def manage_giveaway(callback: CallbackQuery):
    giveaway_id = int(callback.data.split('_')[2])
    giveaway = await get_giveaway_details(giveaway_id)
    
    if not giveaway:
        await callback.answer("Розыгрыш не найден.")
        return
    
    if giveaway.creator_id != callback.from_user.id:
        await callback.answer("Вы не являетесь создателем этого розыгрыша.")
        return
    
    participants = await get_giveaway_participants(giveaway_id)
    
    if not participants:
        await callback.answer("В розыгрыше пока нет участников.")
        return
    
    await callback.message.edit_text(
        f"Управление розыгрышем: {giveaway.name}\n"
        f"Участников: {len(participants)}/{giveaway.max_participants}",
        reply_markup=await giveaway_management_keyboard(giveaway_id)
    )

@dp.callback_query(F.data.startswith('select_winner_'))
async def start_select_winner(callback: CallbackQuery, state: FSMContext):
    giveaway_id = int(callback.data.split('_')[2])
    await state.update_data(giveaway_id=giveaway_id)
    await callback.message.answer("Введите ID пользователя, который выиграл:")
    await state.set_state(GiveawayStates.select_winner)

@dp.message(GiveawayStates.select_winner)
async def process_select_winner(message: Message, state: FSMContext):
    try:
        winner_id = int(message.text)
    except ValueError:
        await message.answer("Введите корректный ID пользователя!")
        return
    
    data = await state.get_data()
    giveaway_id = data['giveaway_id']
    
    # Проверяем, что пользователь действительно участвует в розыгрыше
    is_participant = await check_participant(giveaway_id, winner_id)
    if not is_participant:
        await message.answer("Этот пользователь не участвует в розыгрыше!")
        return
    
    # Завершаем розыгрыш и выбираем победителя
    success = await finish_giveaway(giveaway_id, winner_id)
    if not success:
        await message.answer("Не удалось завершить розыгрыш.")
        return
    
    # Отправляем уведомления участникам
    participants = await get_giveaway_participants(giveaway_id)
    giveaway = await get_giveaway_details(giveaway_id)
    
    for participant in participants:
        try:
            await bot.send_message(
                participant.user_id,
                f"Розыгрыш '{giveaway.name}' завершен!\n\n"
                f"Победитель: @{participant.username if participant.username else 'пользователь'} (ID: {winner_id})\n"
                f"Спасибо за участие!"
            )
        except Exception as e:
            logging.error(f"Не удалось отправить сообщение пользователю {participant.user_id}: {e}")
    
    await message.answer("Розыгрыш успешно завершен! Уведомления отправлены участникам.")
    await state.clear()

# Добавьте в main.py

@dp.message(F.web_app_data)
async def handle_web_app_data(message: Message):
    try:
        data = json.loads(message.web_app_data.data)
        action = data.get('action')
        user_id = message.from_user.id
        
        if action == 'get_giveaway_info':
            giveaway_id = data.get('giveaway_id')
            giveaway = await get_giveaway_details(giveaway_id)
            
            if not giveaway:
                return await message.answer(json.dumps({'error': 'Розыгрыш не найден'}))
            
            channels_info = [{
                'title': channel.title,
                'invite_link': channel.invite_link
            } for channel in giveaway.channels]
            
            return await message.answer(json.dumps({'channels': channels_info}))
        
        elif action == 'check_subscriptions':
            giveaway_id = data.get('giveaway_id')
            giveaway = await get_giveaway_details(giveaway_id)
            channel_ids = [channel.tg_id for channel in giveaway.channels]
            
            is_subscribed = await check_user_subscription(user_id, channel_ids, bot)
            return await message.answer(json.dumps({'all_subscribed': is_subscribed}))
        
        elif action == 'participate':
            giveaway_id = data.get('giveaway_id')
            success = await join_giveaway(giveaway_id, user_id)
            
            if success:
                return await message.answer(json.dumps({'status': 'success'}))
            else:
                return await message.answer(json.dumps({'error': 'Не удалось присоединиться'}))
            
    except Exception as e:
        logging.error(f"WebApp error: {e}")
        return await message.answer(json.dumps({'error': 'Internal server error'}))

@dp.message(Command('get_giveaway_info'))
async def get_giveaway_info(message: Message):
    giveaway_id = message.text.split('=')[1]
    giveaway = await get_giveaway_details(giveaway_id)
    
    channels_info = [{
        'title': channel.title,
        'invite_link': channel.invite_link
    } for channel in giveaway.channels]
    
    await message.answer(json.dumps({
        'channels': channels_info
    }))

@dp.message(Command('check_subscriptions'))
async def check_subscriptions(message: Message):
    data = json.loads(message.text)
    user_id = data['user_id']
    giveaway_id = data['giveaway_id']
    
    giveaway = await get_giveaway_details(giveaway_id)
    channel_ids = [channel.tg_id for channel in giveaway.channels]
    
    is_subscribed = await check_user_subscription(user_id, channel_ids, bot)
    
    await message.answer(json.dumps({
        'all_subscribed': is_subscribed
    }))

async def main():
    await async_main()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
    