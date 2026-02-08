from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..services.excel_service import process_minsa_excel, get_excel_preview, process_excel_async
from ..models import models
from ..auth import get_current_user
import pandas as pd
import io

router = APIRouter(prefix="/excel", tags=["Excel"])

@router.post("/preview")
async def preview_excel(
    file: UploadFile = File(...),
    current_user: models.Usuario = Depends(get_current_user)
):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="El archivo debe ser un Excel (.xlsx o .xls)")
    
    try:
        # Límite para preview: 5MB
        MAX_PREVIEW_SIZE = 5 * 1024 * 1024
        file_size = 0
        content = b""
        while chunk := await file.read(1024 * 100):
            file_size += len(chunk)
            if file_size > MAX_PREVIEW_SIZE:
                raise HTTPException(status_code=413, detail="El archivo es demasiado grande para vista previa. Máximo 5MB.")
            content += chunk
        
        preview_data = get_excel_preview(content)
        return {
            "archivo": file.filename,
            "total_encontrados": len(preview_data),
            "registros": preview_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en vista previa: {str(e)}")

@router.get("/history")
def get_upload_history(db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    try:
        history = db.query(models.CargaExcel).filter(models.CargaExcel.user_id == current_user.id).order_by(models.CargaExcel.created_at.desc()).all()
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo historial: {str(e)}")

@router.get("/export/{anio}/{mes}")
def export_monthly_report(
    anio: int, 
    mes: int, 
    search: str = None,
    eess: str = None,
    estado: str = None,
    solo_nuevos: bool = False,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    try:
        from sqlalchemy import extract, or_, func
        # 1. Base Query - Empezamos por visitas en el periodo
        query = db.query(models.Visita).join(models.Nino).filter(
            extract('month', models.Visita.fecha_visita) == mes,
            extract('year', models.Visita.fecha_visita) == anio,
            models.Visita.user_id == current_user.id
        )

        # Filtro de Niños Nuevos
        if solo_nuevos:
            # Subquery para encontrar la fecha de la primera visita de cada niño
            first_v_subq = db.query(
                models.Visita.nino_id,
                func.min(models.Visita.fecha_visita).label("min_fecha")
            ).group_by(models.Visita.nino_id).subquery()
            
            # Unir con la subquery y filtrar los niños cuya primera visita sea en el mes/año actual
            query = query.join(first_v_subq, models.Visita.nino_id == first_v_subq.c.nino_id).filter(
                extract('month', first_v_subq.c.min_fecha) == mes,
                extract('year', first_v_subq.c.min_fecha) == anio,
                models.Visita.user_id == current_user.id
            )

        # 2. Aplicar Filtros (Misma lógica que en el listado)
        if search:
            search_filt = f"%{search}%"
            query = query.filter(
                or_(
                    models.Nino.dni_nino.ilike(search_filt),
                    models.Nino.nombres.ilike(search_filt),
                    models.Nino.nombre_madre.ilike(search_filt)
                )
            )
        
        if eess:
            query = query.filter(models.Nino.establecimiento_asignado == eess)
        
        if estado:
            query = query.filter(models.Visita.estado == estado.lower())

        # 3. Obtener resultados ordenados
        visitas = query.order_by(models.Nino.nombres).all()
        
        if not visitas:
            raise HTTPException(status_code=404, detail="No se encontraron registros con los filtros seleccionados")
            
        # 4. Agrupar por niño para evitar duplicados (1 fila por niño, como en la tabla UI)
        children_data = {}
        for v in visitas:
            if v.nino_id not in children_data:
                children_data[v.nino_id] = {
                    "DNI Niño": v.nino.dni_nino,
                    "Nombres y Apellidos": v.nino.nombres,
                    "Fecha Nacimiento": v.nino.fecha_nacimiento.strftime('%d/%m/%Y') if v.nino.fecha_nacimiento else '---',
                    "Rango de Edad": v.nino.rango_edad or '---',
                    "Dirección": v.nino.direccion or '---',
                    "DNI Madre": v.nino.dni_madre or '---',
                    "Nombre Madre": v.nino.nombre_madre or '---',
                    "Celular Madre": v.nino.celular_madre or '---',
                    "Actor Social": v.actor_social or '---',
                    "Historia Clinica": v.nino.historia_clinica or '---',
                    "EESS Asignado": v.nino.establecimiento_asignado or '---',
                    "EESS Atención": v.establecimiento_atencion or '---',
                    "Estado": (v.estado or "pendiente").capitalize(),
                    "Visitas en el Mes": 1
                }
            else:
                children_data[v.nino_id]["Visitas en el Mes"] += 1
            
        df = pd.DataFrame(list(children_data.values()))
        
        # 5. Generar archivo Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Reporte Filtrado')
            worksheet = writer.sheets['Reporte Filtrado']
            
            # Formato de cabecera
            header_format = writer.book.add_format({
                'bold': True,
                'bg_color': '#FCE7F3',
                'border': 1
            })
            
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                column_len = max(df[value].astype(str).map(len).max(), len(value)) + 2
                worksheet.set_column(col_num, col_num, min(column_len, 50))
                
        output.seek(0)
        
        suffix = "filtrado" if (search or eess or estado or solo_nuevos) else "completo"
        filename = f"Reporte_{mes}_{anio}_{suffix}.xlsx"
        
        return StreamingResponse(
            output, 
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(f"Error export: {error_msg}")
        raise HTTPException(status_code=500, detail=f"Error generando reporte: {str(e)}\n\nTraceback: {error_msg}")

@router.post("/upload")
async def upload_excel(
    file: UploadFile = File(...),
    mes: int = Form(...),
    anio: int = Form(...),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="El archivo debe ser un Excel (.xlsx o .xls)")
    
    try:
        # Límite de tamaño: 10MB (10 * 1024 * 1024 bytes)
        MAX_SIZE = 10 * 1024 * 1024
        file_size = 0
        content = b""
        
        # Leer en trozos para verificar tamaño sin cargar todo si es excesivo
        while chunk := await file.read(1024 * 100): # 100KB chunks
            file_size += len(chunk)
            if file_size > MAX_SIZE:
                raise HTTPException(status_code=413, detail="El archivo es demasiado grande. Máximo 10MB.")
            content += chunk
        
        # 1. Crear el registro inicial
        nueva_carga = models.CargaExcel(
            nombre_archivo=file.filename,
            mes=mes,
            anio=anio,
            total_registros=0,
            total_repetidos=0,
            user_id=current_user.id,
            estado="procesando"
        )
        db.add(nueva_carga)
        db.commit()
        db.refresh(nueva_carga)
        
        # 2. PROCESAMIENTO SÍNCRONO para feedback inmediato
        try:
            total_visitas, repetidos, nuevos = process_minsa_excel(content, db, mes, anio, current_user.id)
            
            # 3. Actualizar registro y devolver resultados
            nueva_carga.estado = "completado"
            nueva_carga.total_registros = total_visitas
            nueva_carga.total_repetidos = repetidos
            db.commit()
            
            return {
                "message": "Carga completada con éxito.",
                "total_registros": total_visitas,
                "nuevos": nuevos,
                "existentes": repetidos,
                "archivo": file.filename,
                "estado": "completado"
            }
        except Exception as process_error:
            nueva_carga.estado = "error"
            nueva_carga.mensaje_error = str(process_error)[:450]
            db.commit()
            raise HTTPException(status_code=500, detail=f"Error procesando datos: {str(process_error)}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al iniciar carga: {str(e)}")
