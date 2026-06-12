from sqlalchemy import Column, Integer, String, Float, Numeric, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class Group(Base):
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    group_name = Column(String(255), nullable=False)
    description = Column(Text)
    
    users = relationship("User", back_populates="group")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="SET NULL"))
    role = Column(String(50), default='viewer')
    created_at = Column(DateTime, default=func.now())

    group = relationship("Group", back_populates="users")

class FishData(Base):
    __tablename__ = "FishData"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    fish_name = Column(String(255), nullable=False)
    scientific_name = Column(String(255))

class OceanData(Base):
    __tablename__ = "OceanData"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    latitude = Column(Numeric(9, 6), nullable=False)
    longitude = Column(Numeric(9, 6), nullable=False)
    record_timestamp = Column(DateTime, nullable=False)
    sst = Column(Float)
    cha = Column(Float)
    current_speed = Column(Float)
    current_direction = Column(Float)

class EDNAActual(Base):
    __tablename__ = "eDNA_Actual"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    fish_id = Column(Integer, ForeignKey("FishData.id", ondelete="CASCADE"), nullable=False)
    latitude = Column(Numeric(9, 6), nullable=False)
    longitude = Column(Numeric(9, 6), nullable=False)
    sample_timestamp = Column(DateTime, nullable=False)
    concentration = Column(Float)

class EDNAPrediction(Base):
    __tablename__ = "eDNA_Prediction"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    fish_id = Column(Integer, ForeignKey("FishData.id", ondelete="CASCADE"), nullable=False)
    latitude = Column(Numeric(9, 6), nullable=False)
    longitude = Column(Numeric(9, 6), nullable=False)
    target_timestamp = Column(DateTime, nullable=False)
    heatmap_value = Column(Float)

class Hotpoint(Base):
    __tablename__ = "Hotpoint"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    fish_id = Column(Integer, ForeignKey("FishData.id", ondelete="SET NULL"))
    latitude = Column(Numeric(9, 6), nullable=False)
    longitude = Column(Numeric(9, 6), nullable=False)
    detected_timestamp = Column(DateTime, nullable=False)
    intensity_score = Column(Float)

class Suggest(Base):
    __tablename__ = "Suggest"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    hotpoint_id = Column(Integer, ForeignKey("Hotpoint.id", ondelete="SET NULL"))
    fish_id = Column(Integer, ForeignKey("FishData.id", ondelete="SET NULL"))
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now())