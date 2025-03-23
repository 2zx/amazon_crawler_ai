from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.session import Base


class Product(Base):
    """
    Modello dei prodotti Amazon
    """
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    asin = Column(String(10), unique=True, index=True, nullable=False)
    title = Column(String(500), nullable=False)
    url = Column(String(1000), nullable=False)
    price_text = Column(String(50))
    price_value = Column(Float)
    currency = Column(String(3))
    image_url = Column(String(1000))
    category = Column(String(200))
    rating = Column(Float)
    reviews_count = Column(Integer)
    availability = Column(String(200))
    description = Column(Text)
    
    # Metadati
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_checked_at = Column(DateTime, default=datetime.utcnow)
    is_available = Column(Boolean, default=True)
    
    # Relazioni
    price_history = relationship("PriceHistory", back_populates="product")
    specifications = relationship("ProductSpecification", back_populates="product")
    images = relationship("ProductImage", back_populates="product")


class PriceHistory(Base):
    """
    Storico dei prezzi dei prodotti
    """
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    price_text = Column(String(50), nullable=False)
    price_value = Column(Float)
    currency = Column(String(3))
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relazioni
    product = relationship("Product", back_populates="price_history")


class ProductSpecification(Base):
    """
    Specifiche tecniche dei prodotti
    """
    __tablename__ = "product_specifications"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    key = Column(String(200), nullable=False)
    value = Column(Text, nullable=False)
    
    # Relazioni
    product = relationship("Product", back_populates="specifications")


class ProductImage(Base):
    """
    Immagini dei prodotti
    """
    __tablename__ = "product_images"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    url = Column(String(1000), nullable=False)
    position = Column(Integer, default=0)  # Ordine delle immagini
    
    # Relazioni
    product = relationship("Product", back_populates="images")


class TrackingJob(Base):
    """
    Job per il monitoraggio dei prodotti
    """
    __tablename__ = "tracking_jobs"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    name = Column(String(200))
    target_price = Column(Float)
    notify_on_availability = Column(Boolean, default=False)
    notify_on_price_drop = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    notification_email = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_notification_at = Column(DateTime)
    
    # Relazioni
    product = relationship("Product")
