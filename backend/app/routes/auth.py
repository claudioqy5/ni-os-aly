import os
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Cookie
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta, date
from ..database import get_db
from ..models import models
from ..auth import verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, get_password_hash, get_current_user
from ..schemas import schemas
from typing import List
from ..utils.limiter import limiter

# Cargar variables de entorno
load_dotenv()

router = APIRouter(prefix="/auth", tags=["Autenticación"])

@router.post("/login")
@limiter.limit("5/minute")
def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    user = db.query(models.Usuario).filter(models.Usuario.usuario == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if user.is_active == 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Su cuenta ha sido desactivada por el administrador."
        )
    
    if user.fecha_expiracion and user.fecha_expiracion < date.today():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Su permiso de acceso expiró el {user.fecha_expiracion}. Contacte al administrador."
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.usuario}, expires_delta=access_token_expires
    )
    
    # Establecer la cookie HttpOnly
    is_prod = os.getenv("ENV") == "production"
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        expires=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=is_prod, # True en producción con HTTPS
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.usuario,
            "nombre": user.nombre_completo,
            "rol": user.rol
        }
    }

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Sesión cerrada exitosamente"}

@router.post("/setup")
def setup_initial_user(db: Session = Depends(get_db)):
    # Protección Rígida: Si ya hay usuarios, este endpoint queda TOTALMENTE inhabilitado
    existing = db.query(models.Usuario).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="ACCESO DENEGADO: El sistema ya ha sido inicializado. Por seguridad, este endpoint ha sido desactivado permanentemente."
        )
    
    # También verificar una variable de entorno de seguridad
    if os.getenv("ENABLE_SETUP") != "true":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ACCESO DENEGADO: El instalador está desactivado. Habilite ENABLE_SETUP=true en su configuración si desea inicializar."
        )

    new_user = models.Usuario(
        usuario="admin",
        nombre_completo="Administrador Aly",
        password_hash=get_password_hash("admin123"),
        rol="admin"
    )
    db.add(new_user)
    db.commit()
    return {"message": "Usuario administrador inicial creado. Usuario: admin, Clave: admin123. CAMBIE SU CONTRASEÑA DE INMEDIATO."}

# --- ENDPOINTS ADMINISTRATIVOS ---

@router.get("/users", response_model=List[schemas.Usuario])
def list_users(db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    if current_user.rol != "admin":
        raise HTTPException(status_code=403, detail="No tiene permisos para ver esta lista")
    return db.query(models.Usuario).order_by(models.Usuario.id).all()

@router.post("/users", response_model=schemas.Usuario)
def create_user(user: schemas.UsuarioCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    if current_user.rol != "admin":
        raise HTTPException(status_code=403, detail="No tiene permisos para crear usuarios")
    
    existing = db.query(models.Usuario).filter(models.Usuario.usuario == user.usuario).first()
    if existing:
        raise HTTPException(status_code=400, detail="El nombre de usuario ya existe")
    
    if len(user.password) < 8:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 8 caracteres")
    
    db_user = models.Usuario(
        usuario=user.usuario,
        nombre_completo=user.nombre_completo,
        password_hash=get_password_hash(user.password),
        rol=user.rol,
        is_active=user.is_active,
        fecha_expiracion=user.fecha_expiracion
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.put("/users/{user_id}", response_model=schemas.Usuario)
def update_user(user_id: int, user_data: schemas.UsuarioUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    if current_user.rol != "admin":
        raise HTTPException(status_code=403, detail="No tiene permisos para editar usuarios")
    
    db_user = db.query(models.Usuario).filter(models.Usuario.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    if user_data.nombre_completo is not None:
        db_user.nombre_completo = user_data.nombre_completo
    if user_data.rol is not None:
        db_user.rol = user_data.rol
    if user_data.is_active is not None:
        db_user.is_active = user_data.is_active
    if user_data.fecha_expiracion is not None:
        db_user.fecha_expiracion = user_data.fecha_expiracion
    if user_data.password is not None and user_data.password.strip() != "":
        if len(user_data.password) < 8:
            raise HTTPException(status_code=400, detail="La nueva contraseña debe tener al menos 8 caracteres")
        db_user.password_hash = get_password_hash(user_data.password)
        
    db.commit()
    db.refresh(db_user)
    return db_user

@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    if current_user.rol != "admin":
        raise HTTPException(status_code=403, detail="No tiene permisos para eliminar usuarios")
    
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="No puede eliminarse a sí mismo")
        
    db_user = db.query(models.Usuario).filter(models.Usuario.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
    db.delete(db_user)
    db.commit()
    return {"message": "Usuario eliminado correctamente"}

@router.post("/verify-password")
@limiter.limit("5/minute")
async def verify_admin_password(request: Request, data: schemas.VerifyPasswordRequest, current_user: models.Usuario = Depends(get_current_user)):
    if not verify_password(data.password, current_user.password_hash):
        raise HTTPException(status_code=401, detail="Contraseña incorrecta")
    return {"message": "Contraseña verificada"}
