from pydantic import BaseModel, ConfigDict, Field
from datetime import date, datetime
from typing import Optional, List

# Esquemas para Visitas
# Esquemas para Visitas
class VisitaBase(BaseModel):
    estado: Optional[str] = None
    observacion: Optional[str] = None
    fecha_visita: date
    establecimiento_atencion: Optional[str] = None
    actor_social: Optional[str] = None

class VisitaCreate(VisitaBase):
    nino_id: int

class Visita(VisitaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nino_id: int
    created_at: datetime
    updated_at: datetime

# Esquemas para Niños
class NinoBase(BaseModel):
    # dni_nino permite alfanuméricos para soportar Historias Clínicas (ej: "HC - 10511 PS")
    dni_nino: str = Field(..., min_length=3, max_length=50)
    nombres: str = Field(..., min_length=2, max_length=150)
    fecha_nacimiento: Optional[date] = None
    direccion: Optional[str] = Field(None, max_length=250)
    dni_madre: Optional[str] = Field(None, max_length=20)
    nombre_madre: Optional[str] = Field(None, max_length=150)
    celular_madre: Optional[str] = Field(None, max_length=20)
    rango_edad: Optional[str] = Field(None, max_length=50)
    historia_clinica: Optional[str] = Field(None, max_length=50)
    establecimiento_asignado: Optional[str] = Field(None, max_length=150)

class NinoCreate(NinoBase):
    pass

class Nino(NinoBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime
    estado: Optional[str] = None
    es_nuevo: bool = False
    visitas: List[Visita] = []

class NinoListItem(NinoBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    estado: Optional[str] = None
    es_nuevo: bool = False
    visitas_count: int = 0

# Esquemas para Usuarios
class UsuarioBase(BaseModel):
    usuario: str
    nombre_completo: Optional[str] = None
    rol: Optional[str] = "gestor"
    is_active: Optional[int] = 1
    fecha_expiracion: Optional[date] = None

class UsuarioCreate(UsuarioBase):
    password: str = Field(..., min_length=8, max_length=100)

class UsuarioUpdate(BaseModel):
    nombre_completo: Optional[str] = Field(None, max_length=150)
    rol: Optional[str] = None
    is_active: Optional[int] = None
    fecha_expiracion: Optional[date] = None
    password: Optional[str] = Field(None, min_length=8, max_length=100)

class Usuario(UsuarioBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str

class LoginRequest(BaseModel):
    usuario: str
    password: str

class VerifyPasswordRequest(BaseModel):
    password: str

class DeleteReportRequest(BaseModel):
    password: str

# Esquemas para Excel
class CargaExcelBase(BaseModel):
    nombre_archivo: str
    mes: int
    anio: int
    total_registros: int

class CargaExcel(CargaExcelBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
