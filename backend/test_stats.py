from app.database import SessionLocal
from app.models import models
from app.routes.ninos import get_stats

db = SessionLocal()
try:
    # Simular hernan (ID 4)
    user = db.query(models.Usuario).filter(models.Usuario.id == 4).first()
    if not user:
        print("Usuario hernan (ID 4) no encontrado")
    else:
        print(f"Probando stats para: {user.usuario} (ID: {user.id})")
        stats = get_stats(db, user)
        print("Resultado de get_stats:")
        import json
        print(json.dumps(stats, indent=2))
finally:
    db.close()
