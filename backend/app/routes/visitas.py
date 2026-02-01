from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import models
from ..schemas import schemas
from ..auth import get_current_user

router = APIRouter(prefix="/visitas", tags=["Visitas"])

@router.post("/", response_model=schemas.Visita)
def create_visita(visita: schemas.VisitaCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    # Verificar si ya existe una visita para ese niño en esa fecha
    db_visita = db.query(models.Visita).filter(
        models.Visita.nino_id == visita.nino_id,
        models.Visita.fecha_visita == visita.fecha_visita,
        models.Visita.user_id == current_user.id
    ).first()
    
    if db_visita:
        # Si existe, actualizamos
        for key, value in visita.model_dump().items():
            setattr(db_visita, key, value)
    else:
        # Si no existe, creamos
        db_visita = models.Visita(**visita.model_dump(), user_id=current_user.id)
        db.add(db_visita)
    
    db.commit()
    db.refresh(db_visita)
    return db_visita

@router.put("/{visita_id}", response_model=schemas.Visita)
def update_visita(visita_id: int, visita_data: schemas.VisitaCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    db_visita = db.query(models.Visita).filter(models.Visita.id == visita_id, models.Visita.user_id == current_user.id).first()
    if not db_visita:
        raise HTTPException(status_code=404, detail="Visita no encontrada")
    
    for key, value in visita_data.model_dump().items():
        setattr(db_visita, key, value)
    
    db.commit()
    db.refresh(db_visita)
    return db_visita

@router.get("/nino/{nino_id}", response_model=List[schemas.Visita])
def read_visitas_nino(nino_id: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    return db.query(models.Visita).filter(models.Visita.nino_id == nino_id, models.Visita.user_id == current_user.id).all()

@router.get("/resumen")
def get_monthly_summary(db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    # Obtener totales agrupados por mes/anio usando EXTRACT de fecha_visita
    from sqlalchemy import func, extract, case
    
    results = db.query(
        extract('month', models.Visita.fecha_visita).label("mes"),
        extract('year', models.Visita.fecha_visita).label("anio"),
        func.count(models.Visita.id).label("total"),
        func.count(func.distinct(models.Visita.nino_id)).label("totalNinos"),
        # Contar NIÑOS únicos por estado
        func.count(func.distinct(case((models.Visita.estado == 'encontrado', models.Visita.nino_id), else_=None))).label("encontrados"),
        func.count(func.distinct(case((models.Visita.estado == 'no encontrado', models.Visita.nino_id), else_=None))).label("noEncontrados")
    ).filter(
        models.Visita.user_id == current_user.id
    ).group_by(
        extract('month', models.Visita.fecha_visita),
        extract('year', models.Visita.fecha_visita)
    ).order_by(
        extract('year', models.Visita.fecha_visita).desc(),
        extract('month', models.Visita.fecha_visita).desc()
    ).all()
    
    summary = []
    for r in results:
        m = int(r.mes)
        y = int(r.anio)
        summary.append({
            "mes": m,
            "anio": y,
            "month": f"{get_month_name(m)} {y}",
            "total": r.total or 0,
            "totalNinos": r.totalNinos or 0,
            "encontrados": int(r.encontrados or 0),
            "noEncontrados": int(r.noEncontrados or 0)
        })
    return summary

@router.get("/detalle/{anio}/{mes}")
def read_monthly_detail(
    anio: int, 
    mes: int, 
    skip: int = 0, 
    limit: int = 50, 
    search: str = None, 
    eess: str = None,
    estado: str = None,
    solo_nuevos: bool = False,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    try:
        from datetime import date
        from sqlalchemy import func, exists, and_
        
        # Calcular rango de fechas
        start_date = date(anio, mes, 1)
        if mes == 12:
            end_date = date(anio + 1, 1, 1)
        else:
            end_date = date(anio, mes + 1, 1)

        # 1. Identificar niños que tienen visitas en el periodo solicitado
        # Es mucho más eficiente hacer un JOIN o un IN que un EXISTS correlacionado con extract
        visitas_periodo = db.query(models.Visita.nino_id).filter(
            models.Visita.fecha_visita >= start_date,
            models.Visita.fecha_visita < end_date,
            models.Visita.user_id == current_user.id
        )
        
        if estado:
            visitas_periodo = visitas_periodo.filter(models.Visita.estado == estado.lower())
        
        # Obtener IDs únicos de niños para este mes
        query_kids = db.query(models.Nino).filter(models.Nino.id.in_(visitas_periodo))
        
        # Filtro de Niños Nuevos
        if solo_nuevos:
            # Un niño es nuevo si su PRIMERA visita es en este mes/año
            first_v_subq = db.query(
                models.Visita.nino_id,
                func.min(models.Visita.fecha_visita).label("min_fecha")
            ).group_by(models.Visita.nino_id).subquery()
            
            query_kids = query_kids.join(first_v_subq, models.Nino.id == first_v_subq.c.nino_id).filter(
                first_v_subq.c.min_fecha >= start_date,
                first_v_subq.c.min_fecha < end_date
            )

        if search:
            search_filter = f"%{search}%"
            query_kids = query_kids.filter(
                (models.Nino.dni_nino.ilike(search_filter)) |
                (models.Nino.nombres.ilike(search_filter)) |
                (models.Nino.nombre_madre.ilike(search_filter))
            )
        
        if eess:
            query_kids = query_kids.filter(models.Nino.establecimiento_asignado == eess)

        # Total de niños únicos (para paginación)
        total_unique_children = query_kids.count()

        # Obtener los niños de la página actual
        paged_kids = query_kids.order_by(models.Nino.nombres).offset(skip).limit(limit).all()
        child_ids = [k.id for k in paged_kids]

        # 2. Cargar las visitas de este mes para estos niños específicos
        visitas = db.query(models.Visita).filter(
            models.Visita.nino_id.in_(child_ids),
            models.Visita.fecha_visita >= start_date,
            models.Visita.fecha_visita < end_date,
            models.Visita.user_id == current_user.id
        ).all()

        # 3. Datos de estadísticas (Encontrados / No Encontrados) - Respetando filtros
        base_stats_query = db.query(func.count(func.distinct(models.Visita.nino_id))).join(models.Nino).filter(
            models.Visita.fecha_visita >= start_date,
            models.Visita.fecha_visita < end_date,
            models.Visita.user_id == current_user.id
        )
        if solo_nuevos:
             first_v_subq_stat = db.query(
                models.Visita.nino_id,
                func.min(models.Visita.fecha_visita).label("min_fecha")
            ).group_by(models.Visita.nino_id).subquery()
             base_stats_query = base_stats_query.join(first_v_subq_stat, models.Nino.id == first_v_subq_stat.c.nino_id).filter(
                first_v_subq_stat.c.min_fecha >= start_date,
                first_v_subq_stat.c.min_fecha < end_date
            )
        if search:
            base_stats_query = base_stats_query.filter(
                (models.Nino.dni_nino.ilike(search_filter)) |
                (models.Nino.nombres.ilike(search_filter)) |
                (models.Nino.nombre_madre.ilike(search_filter))
            )
        if eess:
            base_stats_query = base_stats_query.filter(models.Nino.establecimiento_asignado == eess)

        encontrados_count = base_stats_query.filter(models.Visita.estado == 'encontrado').scalar() or 0
        no_encon_count = base_stats_query.filter(models.Visita.estado == 'no encontrado').scalar() or 0

        # 4. Primera visita histórica (Eficiente para el flag es_nuevo)
        first_visits = db.query(
            models.Visita.nino_id,
            func.min(models.Visita.fecha_visita).label("primera_fecha")
        ).filter(
            models.Visita.nino_id.in_(child_ids),
            models.Visita.user_id == current_user.id
        ).group_by(models.Visita.nino_id).all()
        
        first_visit_map = {fv.nino_id: fv.primera_fecha for fv in first_visits}
        
        # 5. Mapear resultados
        children_map = {}
        for k in paged_kids:
            primera_f = first_visit_map.get(k.id)
            es_nuevo_item = (primera_f.year == anio and primera_f.month == mes) if primera_f else False

            children_map[k.id] = {
                "id": k.id, "dni": k.dni_nino, "nombres": k.nombres,
                "fecha_nacimiento": k.fecha_nacimiento.strftime('%Y-%m-%d') if k.fecha_nacimiento else '---',
                "rango_edad": k.rango_edad, "historia_clinica": k.historia_clinica,
                "direccion": k.direccion, "dni_madre": k.dni_madre, "nombre_madre": k.nombre_madre,
                "celular_madre": k.celular_madre, "actor_social": None,
                "establecimiento_asignado": k.establecimiento_asignado,
                "establecimiento_atencion": None, "estado": "pendiente",
                "observacion": None, "es_nuevo": es_nuevo_item, "visitas_count": 0
            }

        for v in visitas:
            if v.nino_id in children_map:
                c = children_map[v.nino_id]
                c["visitas_count"] += 1
                c["estado"] = v.estado or "pendiente"
                c["actor_social"] = v.actor_social
                c["establecimiento_atencion"] = v.establecimiento_atencion
                if v.observacion:
                    c["observacion"] = (c["observacion"] + " | " + v.observacion) if c["observacion"] else v.observacion

        final_list = list(children_map.values())
        for c in final_list: c["estado"] = c["estado"].capitalize()
        final_list.sort(key=lambda x: (not x["es_nuevo"], x["nombres"]))
        
        return {
            "total": total_unique_children, 
            "total_children": total_unique_children,
            "encontrados": encontrados_count,
            "no_encontrados": no_encon_count,
            "children": final_list,
            "has_more": (skip + limit) < total_unique_children
        }
    except Exception as e:
        print(f"ERROR EN DETALLE: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/eess/{anio}/{mes}")
def get_monthly_eess(anio: int, mes: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    from sqlalchemy import extract
    # Obtener lista única de EESS asignados para un mes específico
    results = db.query(models.Nino.establecimiento_asignado).join(models.Visita).filter(
        extract('month', models.Visita.fecha_visita) == mes,
        extract('year', models.Visita.fecha_visita) == anio,
        models.Visita.user_id == current_user.id
    ).distinct().all()
    
    eess_list = [r[0] for r in results if r[0]]
    return sorted(eess_list)

@router.get("/eess/all")
def get_all_eess(db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    # Obtener lista única de todos los EESS registrados en el sistema del usuario
    res1 = db.query(models.Nino.establecimiento_asignado).filter(models.Nino.user_id == current_user.id).distinct().all()
    res2 = db.query(models.Visita.establecimiento_atencion).filter(models.Visita.user_id == current_user.id).distinct().all()
    
    # Combinar y limpiar
    eess_set = set()
    for r in res1:
        if r[0]: eess_set.add(r[0])
    for r in res2:
        if r[0]: eess_set.add(r[0])
        
    return sorted(list(eess_set))

@router.delete("/{anio}/{mes}")
def delete_monthly_report(anio: int, mes: int, request: schemas.DeleteReportRequest, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    if not request.password:
        raise HTTPException(status_code=401, detail="Se requiere la contraseña para eliminar")
    
    # Verificar contraseña del usuario actual
    from ..auth import verify_password
    if not verify_password(request.password, current_user.password_hash):
        raise HTTPException(status_code=401, detail="Contraseña de seguridad incorrecta")

    try:
        from sqlalchemy import extract
        # 1. Eliminar visitas
        db.query(models.Visita).filter(
            extract('month', models.Visita.fecha_visita) == mes,
            extract('year', models.Visita.fecha_visita) == anio,
            models.Visita.user_id == current_user.id
        ).delete(synchronize_session=False)
        
        # 2. Eliminar historial de carga excel si existe
        db.query(models.CargaExcel).filter(
            models.CargaExcel.mes == mes,
            models.CargaExcel.anio == anio,
            models.CargaExcel.user_id == current_user.id
        ).delete()
        
        # 3. Limpiar niños huérfanos (que ya no tienen visitas en ningún mes) DEL USUARIO ACTUAL
        # IMPORTANTE: Filtrar por user_id para no afectar a otros usuarios
        orphans = db.query(models.Nino).filter(
            models.Nino.user_id == current_user.id,
            ~models.Nino.visitas.any()
        ).all()
        total_orphans = len(orphans)
        for nino in orphans:
            db.delete(nino)
            
        db.commit()
        return {
            "message": f"Reporte {mes}/{anio} eliminado. Se eliminaron {total_orphans} registros de niños que ya no tenían visitas.",
            "anio": anio,
            "mes": mes
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al eliminar reporte: {str(e)}")

@router.delete("/{visita_id}")
def delete_visita(visita_id: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    db_visita = db.query(models.Visita).filter(models.Visita.id == visita_id, models.Visita.user_id == current_user.id).first()
    if not db_visita:
        raise HTTPException(status_code=404, detail="Visita no encontrada")
    
    try:
        db.delete(db_visita)
        db.commit()
        return {"message": "Visita eliminada con éxito"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al eliminar la visita: {str(e)}")


def get_month_name(n):
    months = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    return months[n-1] if 1 <= n <= 12 else "Mes"
