from sqlalchemy import select
from sqlalchemy.orm import selectinload
import logging
from models import async_session, User, Giveaway, GiveawayParticipant, Channel

async def add_user(tg_user):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_user.id))
        if not user:
            session.add(User(
                tg_id=tg_user.id,
                username=tg_user.username,
                full_name=tg_user.full_name
            ))
            await session.commit()

async def create_giveaway(name, description, max_participants, creator_id):
    async with async_session() as session:
        giveaway = Giveaway(
            name=name,
            description=description,
            max_participants=max_participants,
            creator_id=creator_id
        )
        session.add(giveaway)
        await session.commit()
        return giveaway.id

async def add_channel_to_giveaway(giveaway_id, channel_id):
    async with async_session() as session:
        giveaway = await session.get(Giveaway, giveaway_id, options=[selectinload(Giveaway.channels)])
        channel = await session.get(Channel, channel_id)
        if giveaway and channel:
            if channel not in giveaway.channels:
                giveaway.channels.append(channel)
                await session.commit()
                return True
        return False

async def get_giveaway_channels(giveaway_id):
    async with async_session() as session:
        giveaway = await session.get(Giveaway, giveaway_id, options=[selectinload(Giveaway.channels)])
        return giveaway.channels if giveaway else []

async def check_user_subscription(user_id, channel_ids, bot):
    for channel_id in channel_ids:
        try:
            chat_member = await bot.get_chat_member(channel_id, user_id)
            if chat_member.status not in ["member", "administrator", "creator"]:
                return False
        except Exception as e:
            logging.error(f"Ошибка проверки подписки: {e}")
            return False
    return True

async def create_channel(tg_id, title, invite_link, creator_id):
    async with async_session() as session:
        channel = await session.scalar(select(Channel).where(Channel.tg_id == tg_id))
        if not channel:
            channel = Channel(
                tg_id=tg_id,
                title=title,
                invite_link=invite_link,
                creator_id=creator_id
            )
            session.add(channel)
            await session.commit()
            return channel.id
        return channel.id

async def get_all_give():
    async with async_session() as session:
        return await session.scalars(select(Giveaway).where(Giveaway.is_active == True))

async def get_giveaway_details(giveaway_id):
    async with async_session() as session:
        giveaway = await session.get(Giveaway, giveaway_id, options=[selectinload(Giveaway.channels)])
        if giveaway:
            return giveaway
        return None

async def join_giveaway(giveaway_id, user_id):
    async with async_session() as session:
        giveaway = await session.get(Giveaway, giveaway_id)
        if not giveaway or not giveaway.is_active:
            return False
        
        if giveaway.participants >= giveaway.max_participants:
            return False
        
        existing = await session.scalar(
            select(GiveawayParticipant).where(
                GiveawayParticipant.giveaway_id == giveaway_id,
                GiveawayParticipant.user_id == user_id
            )
        )
        
        if existing:
            return False
        
        session.add(GiveawayParticipant(giveaway_id=giveaway_id, user_id=user_id))
        await session.commit()
        return True
    

async def get_giveaway_participants(giveaway_id):
    async with async_session() as session:
        participants = await session.scalars(
            select(User)
            .join(GiveawayParticipant)
            .where(GiveawayParticipant.giveaway_id == giveaway_id)
        )
        return participants.all()

async def check_participant(giveaway_id, user_id):
    async with async_session() as session:
        participant = await session.scalar(
            select(GiveawayParticipant)
            .where(
                GiveawayParticipant.giveaway_id == giveaway_id,
                GiveawayParticipant.user_id == user_id
            )
        )
        return participant is not None
    
async def set_give_link(give_id, deep_link):
    async with async_session() as session:
        giveaway = await session.get(Giveaway, give_id)
        giveaway.deep_link = deep_link
        await session.commit()

async def finish_giveaway(giveaway_id, winner_id):
    async with async_session() as session:
        giveaway = await session.get(Giveaway, giveaway_id)
        if not giveaway:
            return False
        
        giveaway.is_active = False
        giveaway.winner_id = winner_id
        await session.commit()
        return True