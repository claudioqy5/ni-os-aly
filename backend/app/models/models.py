from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Date, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from ..database import Base
import datetime

class Usuario(Base):
    __tablename__ = "usuario_config"
    id = Column(Integer, primary_key=True, index=True)
    usuario = Column(String(100), unique=True, nullable=False, index=True)
    nombre_completo = Column(String(150))
    password_hash = Column(String, nullable=False)
    rol = Column(String(20), default="gestor") # 'admin', 'gestor'
    is_active = Column(Integer, default=1)
    fecha_expiracion = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.now)

class Nino(Base):
    __tablename__ = "ninos"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("usuario_config.id", ondelete="CASCADE"), nullable=False, index=True)
    dni_nino = Column(String(50), index=True, nullable=False)
    nombres = Column(String(150), nullable=False)
    fecha_nacimiento = Column(Date)
    direccion = Column(String)
    dni_madre = Column(String(50))
    nombre_madre = Column(String(200)) # Aumentamos para nombres largos
    celular_madre = Column(String(50)) # Aumentamos para códigos internacionales
    rango_edad = Column(String(100))
    historia_clinica = Column(String(100))
    establecimiento_asignado = Column(String(255))
    created_at = Column(DateTime, default=datetime.datetime.now)
    updated_at = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    
    __table_args__ = (
        UniqueConstraint('dni_nino', 'user_id', name='_dni_user_uc'),
        Index('idx_nino_user_est', 'user_id', 'establecimiento_asignado'),
    )

    visitas = relationship("Visita", back_populates="nino", cascade="all, delete-orphan")

class Visita(Base):
    __tablename__ = "visitas"
    id = Column(Integer, primary_key=True, index=True)
    nino_id = Column(Integer, ForeignKey("ninos.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("usuario_config.id", ondelete="CASCADE"), nullable=True, index=True)
    estado = Column(String(20), index=True) # 'encontrado', 'no encontrado', 'pendiente'
    observacion = Column(String)
    fecha_visita = Column(Date, nullable=False, index=True)
    establecimiento_atencion = Column(String(150), index=True)
    actor_social = Column(String(150), index=True)
    created_at = Column(DateTime, default=datetime.datetime.now)
    updated_at = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)

    __table_args__ = (
        Index('idx_visita_user_fecha', 'user_id', 'fecha_visita'),
    )

    nino = relationship("Nino", back_populates="visitas")



class CargaExcel(Base):
    __tablename__ = "cargas_excel"
    id = Column(Integer, primary_key=True, index=True)
    nombre_archivo = Column(String(200))
    mes = Column(Integer, nullable=False)
    anio = Column(Integer, nullable=False)
    user_id = Column(Integer, ForeignKey("usuario_config.id", ondelete="CASCADE"), nullable=True, index=True)
    total_registros = Column(Integer)
    total_repetidos = Column(Integer, default=0)
    estado = Column(String(50), default="completado") # 'procesando', 'completado', 'error'
    mensaje_error = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.now)
    updated_at = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)

    __table_args__ = (
        Index('idx_carga_user_periodo', 'user_id', 'anio', 'mes'),
    )
