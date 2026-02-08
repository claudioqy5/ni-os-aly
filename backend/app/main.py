import os
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from .utils.limiter import limiter
from .database import engine
from .models import models
from .routes import auth, ninos, visitas, excel

# Configuración de Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("AlyAPI")

# Configuración de Rate Limiting (SlowAPI)
app = FastAPI(title="Niños Aly API", version="0.1.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.on_event("startup")
def startup_event():
    # Crear las tablas al iniciar
    # models.Base.metadata.create_all(bind=engine)
    print("--- STARTUP SKIPPED CREATE_ALL ---")

# Cargar variables de entorno
load_dotenv()

# Configuración de CORS
origins_env = os.getenv("ALLOWED_ORIGINS", "")
if origins_env:
    origins = [o.strip() for o in origins_env.split(",")]
else:
    if os.getenv("ENV") == "production":
        origins = []
    else:
        origins = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

# Middleware de Seguridad
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    try:
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # CSP: Ajustada para permitir Swagger UI
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https://fastapi.tiangolo.com; "
            "connect-src 'self'"
        )
        response.headers["Content-Security-Policy"] = csp
        return response
    except Exception:
        return await call_next(request)

# Registro de rutas
app.include_router(auth.router)
app.include_router(ninos.router)
app.include_router(visitas.router)
app.include_router(excel.router)

@app.get("/")
async def root():
    return {"message": "Bienvenida Alicia. El backend de Niños Aly está corriendo."}

@app.get("/debug-system")
def debug_system():
    import pkg_resources
    import sys
    installed_packages = {pkg.key: pkg.version for pkg in pkg_resources.working_set}
    return {
        "python_version": sys.version,
        "executable": sys.executable,
        "sys_path": sys.path,
        "installed_packages": installed_packages,
        "xlsxwriter_status": "INSTALLED" if "xlsxwriter" in installed_packages else "MISSING"
    }
