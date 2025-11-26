from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Index, ForeignKey, func, text
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()


class UrlMapping(Base):
    __tablename__ = "url_mappings"

    id = Column(Integer, primary_key=True)
    short_code = Column(String(16), unique=True, nullable=False, index=True)
    original_url = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_by_ip = Column(String(64), nullable=False)
    idempotency_key = Column(String(64), nullable=True, unique=True)
    click_count = Column(Integer, nullable=False, default=0)

    clicks = relationship("ClickEvent", back_populates="url", cascade="all, delete-orphan")

    __table_args__ = (
        Index(
            "ix_url_mappings_active",
            "short_code",
            postgresql_where=text("expires_at IS NULL"),
        ),
    )


class ClickEvent(Base):
    __tablename__ = "click_events"

    id = Column(Integer, primary_key=True)
    short_code = Column(String(16), ForeignKey("url_mappings.short_code", ondelete="CASCADE"), nullable=False, index=True)
    referrer = Column(Text, nullable=True)
    user_agent = Column(Text, nullable=True)
    client_ip = Column(String(64), nullable=False)
    clicked_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    url = relationship("UrlMapping", back_populates="clicks")

    __table_args__ = (
        Index("ix_click_events_clicked_at", "clicked_at"),
    )
