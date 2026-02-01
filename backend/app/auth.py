import os
from dotenv import load_dotenv
from datetime import datetime, timedelta, date
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request, Cookie
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from .database import get_db
from .models import models

# Cargar variables de entorno
load_dotenv()

# Configuración leída desde .env
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    # Solo permitir fallback en local/desarrollo si no hay SECRET_KEY
    # En producción (donde se asume que se definirá una real), esto fallará si no existe
    if os.getenv("ENV") == "production":
        raise RuntimeError("CRITICAL ERROR: SECRET_KEY must be set in production environment!")
    SECRET_KEY = "DEVELOPMENT_SECRET_KEY_CHANGE_IN_PROD"

ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme),
    access_token: Optional[str] = Cookie(None)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    final_token = token
    # Si no hay token en el header, intentar desde el cookie
    if not final_token and access_token:
        if access_token.startswith("Bearer "):
            final_token = access_token.split(" ")[1]
        else:
            final_token = access_token

    if not final_token:
        raise credentials_exception

    try:
        payload = jwt.decode(final_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(models.Usuario).filter(models.Usuario.usuario == username).first()
    if user is None:
        raise credentials_exception
        
    if user.is_active == 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario desactivado. Contacte al administrador."
        )
        
    if user.fecha_expiracion and user.fecha_expiracion < date.today():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Su permiso de acceso expiró el {user.fecha_expiracion}. Contacte al administrador."
        )
        
    return user
