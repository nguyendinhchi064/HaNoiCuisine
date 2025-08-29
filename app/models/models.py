from __future__ import annotations

from datetime import datetime, time
from sqlalchemy import (
    Column, Integer, BigInteger, SmallInteger, Text, Numeric, Time, TIMESTAMP,
    ForeignKey, CheckConstraint, UniqueConstraint, Index, Boolean, Enum as SqlEnum,
    func, text
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.schema import MetaData
from sqlalchemy.dialects.postgresql import ARRAY
from geoalchemy2 import Geography

# ---------- Base ----------
naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
Base = declarative_base(metadata=MetaData(naming_convention=naming_convention))

PlaceStatusEnum = SqlEnum("pending", "approved", "rejected", name="place_status")


# ---------- Users ----------
class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True)
    name = Column(Text)
    email = Column(Text, unique=True)          
    phone = Column(Text)
    password_hash = Column(Text)               
    role = Column(Text, server_default=text("'user'"), nullable=False) 
    is_active = Column(Boolean, nullable=False, server_default=text("true"))

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    reviews = relationship("Review", back_populates="user", lazy="selectin")


# ---------- Places (shareable + moderation) ----------
class Place(Base):
    __tablename__ = "places"

    id = Column(BigInteger, primary_key=True)
    name = Column(Text, nullable=False)
    description = Column(Text)
    address = Column(Text)
    ward = Column(Text)
    district = Column(Text)
    city = Column(Text, server_default=text("'Hà Nội'"))
    phone = Column(Text)
    website = Column(Text)
    price_level = Column(SmallInteger)        # 1 = budget (street food / student-friendly) 2 = moderate 3 = pricey 4 = premium
    rating = Column(Numeric(2, 1))                

    geom = Column(Geography(geometry_type="POINT", srid=4326))  # lon/lat

    # --- Sharing & publishing ---
    slug = Column(Text, unique=True)             
    is_public = Column(Boolean, nullable=False, server_default=text("false"))
    status = Column(PlaceStatusEnum, nullable=False, server_default=text("'pending'"))
    share_token = Column(Text, unique=True)        
    published_at = Column(TIMESTAMP(timezone=True))
    created_by = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))
    updated_by = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    creator = relationship("User", foreign_keys=[created_by], lazy="selectin")
    updater = relationship("User", foreign_keys=[updated_by], lazy="selectin")

    categories = relationship("Category", secondary="place_categories", back_populates="places", lazy="selectin")
    opening_hours = relationship("OpeningHour", back_populates="place", cascade="all, delete-orphan", lazy="selectin")
    menus = relationship("Menu", back_populates="place", cascade="all, delete-orphan", lazy="selectin")
    reviews = relationship("Review", back_populates="place", cascade="all, delete-orphan", lazy="selectin")
    weather_scores = relationship("PlaceWeatherScore", back_populates="place", cascade="all, delete-orphan", lazy="selectin")

    __table_args__ = (
        Index("idx_places_geom", "geom", postgresql_using="gist"),
        Index("idx_places_name_trgm", "name", postgresql_using="gin", postgresql_ops={"name": "gin_trgm_ops"}),
        Index("idx_places_addr_trgm", "address", postgresql_using="gin", postgresql_ops={"address": "gin_trgm_ops"}),
        Index("idx_places_status", "status"),
        Index("idx_places_is_public", "is_public"),
    )


# ---------- Categories / Join ----------
class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True)
    slug = Column(Text, unique=True, nullable=False)
    title = Column(Text, nullable=False)
    places = relationship("Place", secondary="place_categories", back_populates="categories", lazy="selectin")

class PlaceCategory(Base):
    __tablename__ = "place_categories"
    place_id = Column(BigInteger, ForeignKey("places.id", ondelete="CASCADE"), primary_key=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True)


# ---------- Opening hours ----------
class OpeningHour(Base):
    __tablename__ = "opening_hours"
    id = Column(BigInteger, primary_key=True)
    place_id = Column(BigInteger, ForeignKey("places.id", ondelete="CASCADE"), nullable=False)
    weekday = Column(SmallInteger, nullable=False)
    opens = Column(Time, nullable=False)
    closes = Column(Time, nullable=False)
    place = relationship("Place", back_populates="opening_hours")
    __table_args__ = (CheckConstraint("weekday BETWEEN 0 AND 6", name="weekday_range"),)


# ---------- Menus & items ----------
class Menu(Base):
    __tablename__ = "menus"
    id = Column(BigInteger, primary_key=True)
    place_id = Column(BigInteger, ForeignKey("places.id", ondelete="CASCADE"), nullable=False)
    title = Column(Text)
    place = relationship("Place", back_populates="menus")
    items = relationship("MenuItem", back_populates="menu", cascade="all, delete-orphan", lazy="selectin")

class MenuItem(Base):
    __tablename__ = "menu_items"
    id = Column(BigInteger, primary_key=True)
    menu_id = Column(BigInteger, ForeignKey("menus.id", ondelete="CASCADE"), nullable=False)
    name = Column(Text, nullable=False)
    description = Column(Text)
    price = Column(Integer)             # VND
    tags = Column(ARRAY(Text))
    menu = relationship("Menu", back_populates="items", lazy="selectin")          


# ---------- Reviews ----------
class Review(Base):
    __tablename__ = "reviews"
    id = Column(BigInteger, primary_key=True)
    place_id = Column(BigInteger, ForeignKey("places.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    rating = Column(SmallInteger)
    content = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    place = relationship("Place", back_populates="reviews")
    user = relationship("User", back_populates="reviews")
    __table_args__ = (CheckConstraint("rating BETWEEN 1 AND 5", name="rating_range"),)


# ---------- Weather ----------
class WeatherCache(Base):
    __tablename__ = "weather_cache"
    id = Column(BigInteger, primary_key=True)
    lat = Column(Numeric(8, 5))
    lon = Column(Numeric(8, 5))
    ts_hour = Column(TIMESTAMP(timezone=True))
    temp_c = Column(Numeric(4, 1))
    feels_like_c = Column(Numeric(4, 1))
    humidity = Column(SmallInteger)
    condition = Column(Text)
    __table_args__ = (UniqueConstraint("lat", "lon", "ts_hour", name="uq_weather_cache_cell"),)

class PlaceWeatherScore(Base):
    __tablename__ = "place_weather_score"
    place_id = Column(BigInteger, ForeignKey("places.id", ondelete="CASCADE"), primary_key=True)
    weather_bucket = Column(Text, primary_key=True)    # hot/warm/cool/cold/rain
    score = Column(Numeric(3, 2), nullable=False, server_default=text("0"))
    place = relationship("Place", back_populates="weather_scores")
