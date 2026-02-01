from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import models
from ..schemas import schemas
from ..auth import get_current_user
from ..services.pdf_service import generate_child_history_pdf

router = APIRouter(prefix="/ninos", tags=["Niños"])

@router.get("/stats")
def get_stats(db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    from sqlalchemy import func, extract, case
    
    total_ninos = db.query(func.count(models.Nino.id)).filter(models.Nino.user_id == current_user.id).scalar()
    
    # Obtener totales de visitas de una sola vez
    visitas_stats = db.query(
        func.count(models.Visita.id).label("total"),
        func.count(case((models.Visita.estado == 'encontrado', 1))).label("encontrados"),
        func.count(case((models.Visita.estado == 'no encontrado', 1))).label("no_encontrados")
    ).filter(models.Visita.user_id == current_user.id).first()
    
    # Obtener última carga
    ultima_carga = db.query(models.CargaExcel).filter(models.CargaExcel.user_id == current_user.id).order_by(models.CargaExcel.created_at.desc()).first()
    
    repetidos = 0
    nuevos = 0
    total_mes = 0
    mes_nombre = "---"
    
    if ultima_carga:
        from .visitas import get_month_name
        from datetime import date
        mes_nombre = f"{get_month_name(ultima_carga.mes)} {ultima_carga.anio}"
        
        # Calcular rango para la carga
        start_c = date(ultima_carga.anio, ultima_carga.mes, 1)
        if ultima_carga.mes == 12:
            end_c = date(ultima_carga.anio + 1, 1, 1)
        else:
            end_c = date(ultima_carga.anio, ultima_carga.mes + 1, 1)
        
        # Un niño es nuevo este mes si su PRIMERA visita histórica es en el periodo de la carga
        # Primero identificamos niños que ya tenían visitas ANTES de este mes
        viejos_ids = db.query(models.Visita.nino_id).filter(
            models.Visita.user_id == current_user.id,
            models.Visita.fecha_visita < start_c
        ).distinct()
        
        # Nuevos: Niños que tienen visita este mes Y NO están en la lista de 'viejos'
        nuevos = db.query(func.count(func.distinct(models.Visita.nino_id))).filter(
            models.Visita.user_id == current_user.id,
            models.Visita.fecha_visita >= start_c,
            models.Visita.fecha_visita < end_c,
            ~models.Visita.nino_id.in_(viejos_ids)
        ).scalar() or 0
        
        # total_mes: Niños únicos que tuvieron visitas este mes
        total_mes = db.query(func.count(func.distinct(models.Visita.nino_id))).filter(
            models.Visita.fecha_visita >= start_c,
            models.Visita.fecha_visita < end_c,
            models.Visita.user_id == current_user.id
        ).scalar() or 0
        
        repetidos = max(0, total_mes - nuevos)
        
    return {
        "global": {
            "total_ninos": total_ninos,
            "encontrados": visitas_stats.encontrados or 0,
            "no_encontrados": visitas_stats.no_encontrados or 0,
        },
        "mensual": {
            "mes": mes_nombre,
            "nuevos": nuevos,
            "existentes": repetidos,
            "total_mes": total_mes
        }
    }

@router.get("/", response_model=List[schemas.NinoListItem])
def read_ninos(db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    from sqlalchemy import func, outerjoin
    from datetime import date
    
    today = date.today()
    
    # Optimizamos: Traer niños con el estado de su última visita y flag de si es nuevo
    # Subquery para la primera visita (para es_nuevo)
    first_v = db.query(
        models.Visita.nino_id,
        func.min(models.Visita.fecha_visita).label("primera")
    ).group_by(models.Visita.nino_id).subquery()
    
    # Subquery para la última visita (para estado)
    last_v_id = db.query(
        models.Visita.nino_id,
        func.max(models.Visita.id).label("max_id")
    ).group_by(models.Visita.nino_id).subquery()
    
    last_v = db.query(
        models.Visita.nino_id,
        models.Visita.estado
    ).join(last_v_id, models.Visita.id == last_v_id.c.max_id).subquery()
    
    # Consulta principal
    ninos_data = db.query(
        models.Nino,
        last_v.c.estado.label("ultimo_estado"),
        first_v.c.primera.label("primera_visita"),
        func.count(models.Visita.id).label("v_count")
    ).outerjoin(last_v, models.Nino.id == last_v.c.nino_id)\
     .outerjoin(first_v, models.Nino.id == first_v.c.nino_id)\
     .outerjoin(models.Visita, models.Nino.id == models.Visita.nino_id)\
     .filter(models.Nino.user_id == current_user.id)\
     .group_by(models.Nino.id, last_v.c.estado, first_v.c.primera)\
     .all()
    
    result = []
    for nino_obj, est, prim, v_count in ninos_data:
        # Convertir el objeto SQLAlchemy a diccionario base
        nino_dict = {c.name: getattr(nino_obj, c.name) for c in nino_obj.__table__.columns}
        
        # Añadir campos calculados
        nino_dict["estado"] = est or "pendiente"
        nino_dict["visitas_count"] = v_count or 0
        
        # Lógica de es_nuevo
        if prim:
            nino_dict["es_nuevo"] = (prim.year == today.year and prim.month == today.month)
        else:
            nino_dict["es_nuevo"] = False
            
        result.append(nino_dict)
            
    return result

@router.post("/", response_model=schemas.Nino)
def create_nino(nino: schemas.NinoCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    db_nino = db.query(models.Nino).filter(
        models.Nino.dni_nino == nino.dni_nino,
        models.Nino.user_id == current_user.id
    ).first()
    if db_nino:
        raise HTTPException(status_code=400, detail="DNI ya registrado para este usuario")
    db_nino = models.Nino(**nino.model_dump(), user_id=current_user.id)
    db.add(db_nino)
    db.commit()
    db.refresh(db_nino)
    return db_nino

@router.get("/{nino_id}", response_model=schemas.Nino)
def read_nino(nino_id: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    db_nino = db.query(models.Nino).filter(models.Nino.id == nino_id, models.Nino.user_id == current_user.id).first()
    if db_nino is None:
        raise HTTPException(status_code=404, detail="Niño no encontrado o no pertenece a su usuario")
    return db_nino

@router.put("/{nino_id}", response_model=schemas.Nino)
def update_nino(nino_id: int, nino_update: schemas.NinoCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    db_nino = db.query(models.Nino).filter(models.Nino.id == nino_id, models.Nino.user_id == current_user.id).first()
    if db_nino is None:
        raise HTTPException(status_code=404, detail="Niño no encontrado o no tiene permisos")
    
    for key, value in nino_update.model_dump().items():
        setattr(db_nino, key, value)
    
    db.commit()
    db.refresh(db_nino)
    return db_nino

@router.delete("/{nino_id}")
def delete_nino(nino_id: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    db_nino = db.query(models.Nino).filter(models.Nino.id == nino_id, models.Nino.user_id == current_user.id).first()
    if db_nino is None:
        raise HTTPException(status_code=404, detail="Niño no encontrado o no tiene permisos")
    
    db.delete(db_nino)
    db.commit()
    return {"message": "Niño eliminado con éxito"}

@router.get("/{nino_id}/pdf")
def get_nino_pdf(nino_id: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    db_nino = db.query(models.Nino).filter(models.Nino.id == nino_id, models.Nino.user_id == current_user.id).first()
    if not db_nino:
        raise HTTPException(status_code=404, detail="Niño no encontrado")
    
    # Obtener todas sus visitas históricas
    visitas = db.query(models.Visita).filter(models.Visita.nino_id == nino_id, models.Visita.user_id == current_user.id).all()
    
    try:
        pdf_content = generate_child_history_pdf(db_nino, visitas)
        
        filename = f"Historial_{db_nino.dni_nino}.pdf"
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al generar el PDF: {str(e)}")
