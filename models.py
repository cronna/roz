from sqlalchemy import BigInteger, String, ForeignKey, Integer, Boolean, Table, Column
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine, AsyncSession


engine = create_async_engine(url='sqlite+aiosqlite:///giveaway.sqlite3')
async_session = async_sessionmaker(
    engine, 
    class_=AsyncSession,
    expire_on_commit=False
)

class Base(AsyncAttrs, DeclarativeBase):
    pass

giveaway_channels = Table(
    'giveaway_channels',
    Base.metadata,
    Column('giveaway_id', Integer, ForeignKey('giveaways.id'), primary_key=True),
    Column('channel_id', BigInteger, ForeignKey('channels.id'), primary_key=True)
)

class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    username: Mapped[str] = mapped_column(String(50), nullable=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=True)

class Giveaway(Base):
    __tablename__ = 'giveaways'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(500))
    participants: Mapped[int] = mapped_column(default=0)
    max_participants: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    creator_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.tg_id'))
    winner_id = mapped_column(BigInteger, nullable=True)
    deep_link = mapped_column(String(200), default='')  # Новое поле
    channels: Mapped[list["Channel"]] = relationship(secondary=giveaway_channels)

class GiveawayParticipant(Base):
    __tablename__ = 'giveaway_participants'

    giveaway_id: Mapped[int] = mapped_column(ForeignKey('giveaways.id'), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.tg_id'), primary_key=True)

class Channel(Base):
    __tablename__ = 'channels'

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    title: Mapped[str] = mapped_column(String(100))
    invite_link: Mapped[str] = mapped_column(String(200), nullable=True)
    creator_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.tg_id'))

async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)