"""Database management for property listings."""
import os
from datetime import datetime
from typing import List, Optional
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()


class Property(Base):
    """Property listing model."""

    __tablename__ = 'properties'

    id = Column(Integer, primary_key=True)
    external_id = Column(String(255), unique=True, nullable=False, index=True)
    source = Column(String(100), nullable=False)
    title = Column(String(500), nullable=False)
    price = Column(String(100))
    location = Column(String(300))
    bedrooms = Column(String(50))
    area = Column(String(100))
    url = Column(Text, nullable=False)
    description = Column(Text)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    notified = Column(Boolean, default=False)

    def __repr__(self):
        return f"<Property(title='{self.title}', source='{self.source}', price='{self.price}')>"


class Database:
    """Database manager for property listings."""

    def __init__(self, database_url: Optional[str] = None):
        """Initialize database connection."""
        self.database_url = database_url or os.getenv('DATABASE_URL', 'sqlite:///properties.db')
        self.engine = create_engine(self.database_url)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def add_property(self, property_data: dict) -> bool:
        """
        Add a new property to the database or update if exists.

        Args:
            property_data: Dictionary containing property information

        Returns:
            True if new property was added, False if updated
        """
        external_id = property_data.get('external_id')

        # Check if property already exists
        existing = self.session.query(Property).filter_by(external_id=external_id).first()

        if existing:
            # Update last_seen timestamp
            existing.last_seen = datetime.utcnow()
            existing.is_active = True
            self.session.commit()
            return False

        # Create new property
        new_property = Property(
            external_id=external_id,
            source=property_data.get('source'),
            title=property_data.get('title'),
            price=property_data.get('price'),
            location=property_data.get('location'),
            bedrooms=property_data.get('bedrooms'),
            area=property_data.get('area'),
            url=property_data.get('url'),
            description=property_data.get('description', ''),
            notified=False
        )

        self.session.add(new_property)
        self.session.commit()
        return True

    def get_new_properties(self, limit: Optional[int] = None) -> List[Property]:
        """
        Get properties that haven't been notified yet.

        Args:
            limit: Maximum number of properties to return

        Returns:
            List of Property objects
        """
        query = self.session.query(Property).filter_by(notified=False, is_active=True)

        if limit:
            query = query.limit(limit)

        return query.all()

    def mark_as_notified(self, property_id: int):
        """Mark a property as notified."""
        prop = self.session.query(Property).filter_by(id=property_id).first()
        if prop:
            prop.notified = True
            self.session.commit()

    def mark_old_listings_inactive(self, days: int = 7):
        """Mark listings as inactive if not seen in specified days."""
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        self.session.query(Property).filter(
            Property.last_seen < cutoff_date,
            Property.is_active == True
        ).update({Property.is_active: False})

        self.session.commit()

    def get_statistics(self) -> dict:
        """Get database statistics."""
        total = self.session.query(Property).count()
        active = self.session.query(Property).filter_by(is_active=True).count()
        notified = self.session.query(Property).filter_by(notified=True).count()
        pending = self.session.query(Property).filter_by(notified=False, is_active=True).count()

        return {
            'total': total,
            'active': active,
            'notified': notified,
            'pending': pending
        }

    def close(self):
        """Close database connection."""
        self.session.close()
