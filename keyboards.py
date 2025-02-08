from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from requests import *

def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Создать розыгрыш")],
            [KeyboardButton(text="Мои розыгрыши")]
        ],
        resize_keyboard=True
    )

async def pagination_keyboard(page):
    all_give = await get_all_give()
    if not all_give:
        return InlineKeyboardMarkup(inline_keyboard=[])
    
    all_give_list = list(all_give)
    total_pages = (len(all_give_list) + 4) // 5
    page = max(1, min(page, total_pages))
    
    start_idx = (page - 1) * 5
    end_idx = start_idx + 5
    
    builder = InlineKeyboardBuilder()
    for giveaway in all_give_list[start_idx:end_idx]:
        builder.add(InlineKeyboardButton(
            text=giveaway.name,
            callback_data=f"giveaway_{giveaway.id}"
        ))
    builder.adjust(1)
    
    pagination_buttons = []
    if page > 1:
        pagination_buttons.append(InlineKeyboardButton(text="←", callback_data=f"page_{page-1}"))
    pagination_buttons.append(InlineKeyboardButton(text=str(page), callback_data="current_page"))
    if page < total_pages:
        pagination_buttons.append(InlineKeyboardButton(text="→", callback_data=f"page_{page+1}"))
    
    if pagination_buttons:
        builder.row(*pagination_buttons)
    
    return builder.as_markup()

def giveaway_details_keyboard(giveaway_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Участвовать", callback_data=f"join_{giveaway_id}")],
        [InlineKeyboardButton(text='Выбрать победителя', callback_data=f"select_winner_{giveaway_id}")],
        [InlineKeyboardButton(text="Назад", callback_data="my_giveaways")]
    ])

add_channel_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Добавить канал", callback_data="add_channel")]
])

async def channels_subscription_keyboard(giveaway_id):
    giveaway = await get_giveaway_details(giveaway_id)
    if not giveaway or not giveaway.channels:
        return None
    
    builder = InlineKeyboardBuilder()
    
    for channel in giveaway.channels:
        if channel.invite_link:
            builder.button(
                text=f"📢 {channel.title}",
                url=channel.invite_link
            )
    
    builder.button(
        text="✅ Проверить подписку",
        callback_data=f"check_subscription_{giveaway_id}"
    )
    
    builder.adjust(1)
    return builder.as_markup()


async def giveaway_management_keyboard(giveaway_id):
    builder = InlineKeyboardBuilder()
    
    builder.button(
        text="🎉 Выбрать победителя",
        callback_data=f"select_winner_{giveaway_id}"
    )
    
    builder.button(
        text="⬅️ Назад",
        callback_data=f"giveaway_{giveaway_id}"
    )
    
    builder.adjust(1)
    return builder.as_markup()