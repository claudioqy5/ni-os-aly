from app.database import SessionLocal
from app.models import models
from sqlalchemy import func

db = SessionLocal()
try:
    print("--- DIAGNÓSTICO DE BASE DE DATOS ---")
    users = db.query(models.Usuario).all()
    print(f"Total Usuarios: {len(users)}")
    for u in users:
        n_count = db.query(func.count(models.Nino.id)).filter(models.Nino.user_id == u.id).scalar()
        v_count = db.query(func.count(models.Visita.id)).filter(models.Visita.user_id == u.id).scalar()
        c_count = db.query(func.count(models.CargaExcel.id)).filter(models.CargaExcel.user_id == u.id).scalar()
        print(f"Usuario: {u.usuario} (ID: {u.id}, Rol: {u.rol})")
        print(f"  - Niños: {n_count}")
        print(f"  - Visitas: {v_count}")
        print(f"  - Cargas: {c_count}")
    
    total_raw_n = db.query(func.count(models.Nino.id)).scalar()
    print(f"\nTotal Niños en tabla (sin filtrar): {total_raw_n}")
finally:
    db.close()
