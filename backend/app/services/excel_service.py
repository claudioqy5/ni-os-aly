import pandas as pd
import logging
from sqlalchemy.orm import Session
from ..models import models
from datetime import datetime, date
from ..database import SessionLocal
import io
import traceback

logger = logging.getLogger("AlyAPI.Excel")

def clean_document_value(val):
    """
    Limpia y normaliza documentos de identidad (DNI, CNV, RN, Pasaporte, etc.)
    Asegura que no se pierdan ceros a la izquierda y maneja formatos numéricos de Excel.
    """
    if val is None or (isinstance(val, float) and pd.isna(val)) or str(val).strip() == "":
        return None
    
    # Convertir a string y limpiar espacios
    val_str = str(val).strip()
    
    # 1. Si Pandas lo leyó como float (ej: 123456.0), quitar el decimal
    if '.' in val_str:
        parts = val_str.split('.')
        # Si la parte decimal es solo ceros (ej: .0, .00), la descartamos
        if len(parts) > 1 and all(c == '0' for c in parts[1]):
            val_str = parts[0]
            
    # 2. Restaurar ceros si parece ser un DNI estándar (8 dígitos o menos)
    # Solo si es puramente numérico
    if val_str.isdigit():
        if len(val_str) < 8:
            return val_str.zfill(8)
        return val_str
        
    # 3. Si tiene letras o caracteres especiales, truncar a un máximo razonable
    return val_str[:20]

def normalize_text(text):
    """Quita acentos y normaliza texto para comparaciones robustas"""
    if not text or pd.isna(text):
        return ""
    import unicodedata
    text = str(text).strip().upper()
    # Quitar acentos
    text = "".join(c for c in unicodedata.normalize('NFD', text)
                  if unicodedata.category(c) != 'Mn')
    return text

def normalize_eess_name(name):
    """Normaliza el nombre de un EESS quitando prefijos redundantes"""
    if not name or pd.isna(name):
        return None
    
    # Limpieza básica
    name = str(name).strip().upper()
    
    # Prefijos a eliminar (ordenados por longitud de mayor a menor)
    prefixes = [
        'PUESTO DE SALUD', 'CENTRO DE SALUD', 
        'P.S.', 'C.S.', 'PS.', 'CS.', 'PS ', 'CS '
    ]
    
    for prefix in prefixes:
        if name.startswith(prefix):
            name = name[len(prefix):].strip()
            # Si después de quitar el prefijo queda algo como "- " o ". ", lo quitamos
            if name.startswith(('- ', '. ', '/ ')):
                name = name[2:].strip()
            elif name.startswith(('-', '.', '/')):
                name = name[1:].strip()
            break
            
    return name

def normalize_status(text):
    """Normaliza el estado de la visita con búsqueda inteligente"""
    if not text or pd.isna(text):
        return "pendiente"
    
    text = str(text).strip().lower()
    
    # Búsqueda de "no encontrado" (incluye plurales y variantes)
    # Ejemplo: "no encontrado", "no_encontrado", "no encontrados"
    if 'no' in text and ('encontrado' in text or 'encontrados' in text):
        return "no encontrado"
    
    # Búsqueda de "encontrado" (incluye plurales)
    # Ejemplo: "encontrado", "encontrados"
    if 'encontrado' in text or 'encontrados' in text:
        return "encontrado"
    
    # Por defecto
    return "pendiente"

def get_mapped_dataframe(file_content: bytes, nrows=None):
    """Función auxiliar para obtener el DataFrame mapeado y limpio de todas las hojas válidas"""
    xls = pd.ExcelFile(io.BytesIO(file_content))
    all_dfs = []
    
    trigger_words = ['DNI', 'DOCUMENTO', 'NOMBRES', 'PACIENTE', 'NIÑO', 'NIÑOS', 'APELLIDOS', 'IDENTIDAD']
    
    for sheet_name in xls.sheet_names:
        # Mini lectura para detectar si es una hoja de datos
        df_detect = pd.read_excel(xls, sheet_name=sheet_name, header=None, nrows=30)
        
        header_row = None
        for i in range(len(df_detect)):
            row_text = " ".join([str(val).strip().upper() for val in df_detect.iloc[i] if pd.notna(val)])
            if any(word in row_text for word in trigger_words):
                if sum(1 for word in ['DNI', 'NOMBRE', 'DOCUMENTO', 'APELLIDO'] if word in row_text) >= 1:
                    header_row = i
                    break
        
        if header_row is not None:
            df_sheet = pd.read_excel(xls, sheet_name=sheet_name, header=header_row, nrows=nrows)
            
            # Aplicar mapeo de columnas similar al anterior
            alias_config = [
                ('dni_madre', ['DNI MADRE', 'DNI DE LA MADRE', 'DOCUMENTO MADRE', 'DNI MAD']),
                ('nombre_madre', ['NOMBRE MADRE', 'NOMBRE DE LA MADRE', 'NOMBRES MADRE', 'NOMBRE DE MADRE']),
                ('celular_madre', ['CELULAR DE LA MADRE', 'CELULAR MADRE', 'TELEFONO MADRE', 'CELULAR MAD']),
                ('actor_social', ['ACTOR SOCIAL', 'PROMOTOR', 'ACTOR_SOCIAL', 'NOMBRES DEL ACTOR SOCIAL']),
                ('dni_nino', ['DOCUMENTO DEL NIÑO', 'DOCUMENTO DEL NINO', 'DNI NIÑO', 'DNI NINO', 'DNI', 'IDENTIDAD', 'DOC', 'NUMERO DE DOCUMENTO', 'Nro Documento', 'DOCUMENTO']),
                ('nombres', ['NOMBRE DEL NIÑO', 'NOMBRE DEL NINO', 'NOMBRE', 'NOMBRES', 'PACIENTE', 'NIÑO', 'NIÑA', 'NOMBRES COMPLETOS', 'NOMBRE NIÑO', 'NOMBRE NIÑA']),
                ('fecha_nacimiento', ['FECHA DE NACIMIENTO', 'NACIMIENTO', 'F. NAC', 'FECHA NAC', 'F_NACIMIENTO', 'F.NACIMIENTO', 'FEC.NAC']),
                ('direccion', ['DIRECCION', 'DOMICILIO', 'DIRECCIÓN', 'ZONA', 'MANZANA', 'SECTOR', 'DIRECCION']),
                ('establecimiento_asignado', ['EESS', 'ESTABLECIMIENTO', 'CENTRO DE SALUD', 'SALUD', 'ESTABLECIMIENTO_ASIGNADO', 'IPRESS', 'ESTABLECIMIENTO DE SALUD', 'E.E.S.S']),
                ('historia_clinica', ['HISTORIA', 'H.C.', 'EXPEDIENTE', 'HC', 'HISTORIA CLINICA']),
                ('estado', ['ESTADO', 'ESTADO VISITA', 'CONDICION', 'SITUACION', 'ESTADO DEL MES']),
                ('observacion', ['OBSERVACION', 'OBSERVACIÓN', 'OBSERVACIONES', 'MOTIVO', 'COMENTARIO', 'OBS', 'OBSER']),
                ('rango_edad', ['RANGO DE EDAD', 'EDAD', 'ETAPA DE VIDA', 'RANGO_EDAD']),
                ('nro_visitas', ['NRO VISITA', 'NUMERO DE VISITA', 'VISITA', 'NRO_VISITA', 'TOTAL VISITAS', 'NUMERO DE VISITAS', 'VISITAS']),
                ('establecimiento_atencion', ['ESTABLECIMIENTO DE ATENCION', 'EESS ATENCION', 'EESS DONDE SE ATIENDE', 'DONDE SE ATIENDE', 'LUGAR DE ATENCION'])
            ]
            
            # Aplicar mapeo de columnas más inteligente
            mapping = {}
            used_cols = set()
            
            # 1. Primero intentar coincidencias exactas para mayor precisión
            for std_name, aliases in alias_config:
                for idx, col in enumerate(df_sheet.columns):
                    if idx in used_cols: continue
                    col_norm = normalize_text(col)
                    if any(normalize_text(a) == col_norm for a in aliases):
                        mapping[col] = std_name
                        used_cols.add(idx)
                        break
            
            # 2. Luego coincidencias parciales más inteligentes
            for std_name, aliases in alias_config:
                if std_name in [m for m in mapping.values()]: continue
                
                for idx, col in enumerate(df_sheet.columns):
                    if idx in used_cols: continue
                    col_norm = normalize_text(col)
                    
                    for a in aliases:
                        a_norm = normalize_text(a)
                        if len(a_norm) <= 4:
                            is_match = a_norm == col_norm or f" {a_norm} " in f" {col_norm} " or col_norm.startswith(f"{a_norm} ") or col_norm.endswith(f" {a_norm}")
                        else:
                            is_match = a_norm in col_norm
                            
                        if is_match:
                            if std_name in ['dni_nino', 'nombres'] and any(x in col_norm for x in ['MADRE', 'ACTOR', 'PADRE']): 
                                continue
                            if std_name == 'nro_visitas' and any(x in col_norm for x in ['FECHA', 'ESTADO', 'DNI', 'MADRE']):
                                continue
                                
                            mapping[col] = std_name
                            used_cols.add(idx)
                            break
                    if idx in used_cols: break
            
            if mapping:
                df_sheet = df_sheet.rename(columns=mapping)
                final_cols = [c for c in df_sheet.columns if c in mapping.values()]
                df_sheet = df_sheet[final_cols]
                all_dfs.append(df_sheet)

                
        # Si es preview y ya tenemos algo, paramos para velocidad
        if nrows and all_dfs: break

    if not all_dfs:
        return pd.DataFrame()
        
    return pd.concat(all_dfs, ignore_index=True)

def get_excel_preview(file_content: bytes):
    try:
        # Cargamos todo el contenido para la vista previa según petición del usuario
        df_preview = get_mapped_dataframe(file_content)
        
        unique_children = {}
        
        for _, row in df_preview.iterrows():
            dni_val = row.get('dni_nino')
            hc_val = row.get('historia_clinica')
            
            if (pd.isna(dni_val) or str(dni_val).strip() == ""):
                if pd.notna(hc_val) and str(hc_val).strip() != "":
                    dni = f"HC-{str(hc_val).strip()}"
                else: continue
            else:
                dni = clean_document_value(dni_val)
                if not dni: continue
            
            if dni in unique_children: continue

            fecha_nac = '---'
            if pd.notna(row.get('fecha_nacimiento')):
                try:
                    fecha_val = row.get('fecha_nacimiento')
                    if isinstance(fecha_val, (int, float)):
                        fecha_nac = pd.to_datetime(fecha_val, origin='1899-12-30', unit='D').strftime('%d/%m/%Y')
                    else:
                        fecha_nac = pd.to_datetime(str(fecha_val), dayfirst=True, errors='coerce').strftime('%d/%m/%Y')
                except: pass

            unique_children[dni] = {
                'dni_nino': dni,
                'nombres': str(row.get('nombres', 'SIN NOMBRE')).strip().upper()[:100],
                'fecha_nacimiento': fecha_nac,
                'direccion': str(row.get('direccion', ''))[:100] if pd.notna(row.get('direccion')) else '',
                'dni_madre': str(row.get('dni_madre', ''))[:15] if pd.notna(row.get('dni_madre')) else '',
                'nombre_madre': str(row.get('nombre_madre', ''))[:100] if pd.notna(row.get('nombre_madre')) else '',
                'celular_madre': str(row.get('celular_madre', ''))[:15] if pd.notna(row.get('celular_madre')) else '',
                'actor_social': str(row.get('actor_social', ''))[:50] if pd.notna(row.get('actor_social')) else '',
                'establecimiento_asignado': normalize_eess_name(row.get('establecimiento_asignado'))[:50] if pd.notna(row.get('establecimiento_asignado')) else '',
                'historia_clinica': str(row.get('historia_clinica', ''))[:50] if pd.notna(row.get('historia_clinica')) else '',
                'rango_edad': str(row.get('rango_edad', ''))[:50] if pd.notna(row.get('rango_edad')) else '',
                'estado': normalize_status(row.get('estado')).upper(),
                'observacion': str(row.get('observacion', ''))[:150] if pd.notna(row.get('observacion')) else '',
                'establecimiento_atencion': normalize_eess_name(row.get('establecimiento_atencion'))[:100] if pd.notna(row.get('establecimiento_atencion')) else ''
            }
        return list(unique_children.values())
    except Exception as e:
        print(f"Error en vista previa: {e}")
        return []

def process_minsa_excel(file_content: bytes, db: Session, mes: int, anio: int, user_id: int, eess_filter: str = None):
    try:
        print(f"--- Iniciando procesamiento Excel: {mes}/{anio} ---")
        df = get_mapped_dataframe(file_content)
        if df.empty:
            return 0, 0, 0
            
        # 1. Limpieza Vectorizada y Garantía de Columnas
        def clean_dni_val(val):
            return clean_document_value(val)

        # Garantizar que las columnas mínimas existen para evitar KeyErrors
        expected_cols = [
            'nombres', 'direccion', 'dni_madre', 'nombre_madre', 
            'celular_madre', 'rango_edad', 'historia_clinica', 
            'establecimiento_asignado', 'estado', 'observacion', 
            'actor_social', 'establecimiento_atencion', 'dni_nino'
        ]
        for col in expected_cols:
            if col not in df.columns:
                df[col] = None

        # Crear columna DNI final de forma eficiente
        df['dni_final'] = df.apply(lambda r: clean_dni_val(r.get('dni_nino')) or 
                                 (f"HC-{str(r.get('historia_clinica')).strip()}" if pd.notna(r.get('historia_clinica')) and str(r.get('historia_clinica')).strip() != "" else None), axis=1)
        df = df.dropna(subset=['dni_final'])
        
        if df.empty:
            return 0, 0, 0

        # Normalizaciones masivas de forma segura
        df['nombres'] = df['nombres'].fillna('SIN NOMBRE').astype(str).str.strip().str.upper().str.slice(0, 150)
        df['direccion'] = df['direccion'].fillna('').astype(str).str.slice(0, 250)
        df['dni_madre'] = df['dni_madre'].apply(clean_dni_val).str.slice(0, 15)
        df['nombre_madre'] = df['nombre_madre'].fillna('').astype(str).str.slice(0, 150)
        df['celular_madre'] = df['celular_madre'].apply(clean_dni_val).str.slice(0, 15)
        df['rango_edad'] = df['rango_edad'].fillna('').astype(str).str.slice(0, 50)
        df['historia_clinica'] = df['historia_clinica'].fillna('').astype(str).str.slice(0, 50)
        
        # Aplicar filtro de EESS si existe
        if eess_filter:
            df['establecimiento_normalizado'] = df['establecimiento_asignado'].apply(
                lambda x: normalize_eess_name(x) if pd.notna(x) else None
            )
            eess_filter_normalizado = normalize_eess_name(eess_filter)
            df = df[df['establecimiento_normalizado'] == eess_filter_normalizado]
            df = df.drop(columns=['establecimiento_normalizado'])
            
            if df.empty:
                print(f"No se encontraron registros para el EESS: {eess_filter}")
                return 0, 0, 0
        
        # 2. Precargar Datos de la DB (Solo del usuario actual)
        unique_dnis = df['dni_final'].unique().tolist()
        existing_kids = {k.dni_nino: k for k in db.query(models.Nino).filter(models.Nino.dni_nino.in_(unique_dnis), models.Nino.user_id == user_id).all()}
        
        v_date = date(anio, mes, 1)
        
        # 3. Precargar Visitas existentes para los niños identificados (SOLO EN EL MES/AÑO)
        # Esto evita el NameError y optimiza el proceso
        existing_visits_list = db.query(models.Visita).filter(
            models.Visita.nino_id.in_([k.id for k in existing_kids.values()]),
            models.Visita.fecha_visita == v_date
        ).all()
        
        # Organizar por nino_id para acceso rápido
        existing_visits = {}
        for ev in existing_visits_list:
            if ev.nino_id not in existing_visits:
                existing_visits[ev.nino_id] = []
            existing_visits[ev.nino_id].append(ev)

        # 4. Preparar estructuras para Bulk Operations
        ninos_to_update = []
        ninos_to_create = []
        visitas_to_create = []
        visitas_to_update = []
        
        # Estructura local para visitas de niños nuevos (evita fugas de estado global)
        pending_visits_new_kids = []

        nuevos_ninos_cnt = 0
        repetidos_ninos_cnt = 0
        total_visitas_procesadas = 0

        grouped = df.groupby('dni_final')
        
        for dni, group in grouped:
            main_row = group.iloc[0]
            db_nino = existing_kids.get(dni)
            
            nino_fields = {
                'dni_nino': dni, 
                'nombres': main_row.get('nombres', 'SIN NOMBRE'), 
                'direccion': main_row.get('direccion', ''),
                'dni_madre': main_row.get('dni_madre'), 
                'nombre_madre': main_row.get('nombre_madre', ''),
                'celular_madre': main_row.get('celular_madre'), 
                'establecimiento_asignado': normalize_eess_name(main_row.get('establecimiento_asignado'))[:150] if pd.notna(main_row.get('establecimiento_asignado', None)) else None,
                'historia_clinica': main_row.get('historia_clinica', ''), 
                'rango_edad': main_row.get('rango_edad', ''),
                'user_id': user_id
            }
            
            if pd.notna(main_row.get('fecha_nacimiento')):
                try:
                    f_val = main_row['fecha_nacimiento']
                    if isinstance(f_val, (int, float)): 
                        nino_fields['fecha_nacimiento'] = pd.to_datetime(f_val, origin='1899-12-30', unit='D').date()
                    else: 
                        # Intentar parsear formato estándar día/mes/año primero
                        nino_fields['fecha_nacimiento'] = pd.to_datetime(str(f_val), dayfirst=True, errors='coerce').date()
                except: pass

            if db_nino:
                repetidos_ninos_cnt += 1
                update_data = {'id': db_nino.id}
                for k, v in nino_fields.items():
                    if v and str(v).lower() not in ["", "nan", "none", "---"]:
                        update_data[k] = v
                ninos_to_update.append(update_data)
                target_nino_id = db_nino.id
            else:
                nuevos_ninos_cnt += 1
                # Guardamos fields para crear después
                nino_to_create_obj = models.Nino(**nino_fields)
                ninos_to_create.append(nino_to_create_obj)
                target_nino_id = None 

            # Lógica de Visitas
            nro_v_max = len(group)
            if 'nro_visitas' in group.columns:
                try:
                    v_col_max = int(pd.to_numeric(group['nro_visitas'], errors='coerce').max() or 1)
                    nro_v_max = max(nro_v_max, v_col_max)
                except: pass
            
            if nro_v_max > 10: nro_v_max = 1

            estado_final = normalize_status(main_row.get('estado'))
            obs_val = str(main_row.get('observacion'))[:500] if pd.notna(main_row.get('observacion')) else None
            eess_at_val = normalize_eess_name(main_row.get('establecimiento_atencion'))[:150] if pd.notna(main_row.get('establecimiento_atencion')) else None
            actor_val = str(main_row.get('actor_social'))[:150] if pd.notna(main_row.get('actor_social')) else None

            # Si el niño ya existe, podemos preparar las visitas ahora
            if target_nino_id:
                v_est = existing_visits.get(target_nino_id, [])
                for i in range(nro_v_max):
                    v_data = {
                        'nino_id': target_nino_id,
                        'estado': estado_final,
                        'observacion': obs_val,
                        'fecha_visita': v_date,
                        'establecimiento_atencion': eess_at_val,
                        'actor_social': actor_val,
                        'user_id': user_id
                    }
                    if i < len(v_est):
                        v_data['id'] = v_est[i].id
                        visitas_to_update.append(v_data)
                    else:
                        visitas_to_create.append(v_data)
            else:
                # Para niños nuevos, guardamos la info para procesar tras el flush
                pending_visits_new_kids.append({
                    'dni': dni,
                    'nro_v_max': nro_v_max,
                    'estado': estado_final,
                    'obs': obs_val,
                    'eess_at': eess_at_val,
                    'actor': actor_val
                })

            total_visitas_procesadas += nro_v_max

        # 5. Ejecutar Bulk Operations en orden
        if ninos_to_update:
            db.bulk_update_mappings(models.Nino, ninos_to_update)
        
        if ninos_to_create:
            for nino_obj in ninos_to_create:
                db.add(nino_obj)
            db.flush() # Genera IDs para los nuevos niños
            
            # Ahora procesar visitas pendientes de niños nuevos
            # Mapeamos los DNIs a los nuevos IDs generados
            new_kids_map = {k.dni_nino: k.id for k in ninos_to_create}
            
            for p in pending_visits_new_kids:
                kid_id = new_kids_map.get(p['dni'])
                if kid_id:
                    for _ in range(p['nro_v_max']):
                        visitas_to_create.append({
                            'nino_id': kid_id,
                            'estado': p['estado'],
                            'observacion': p['obs'],
                            'fecha_visita': v_date,
                            'establecimiento_atencion': p['eess_at'],
                            'actor_social': p['actor'],
                            'user_id': user_id
                        })

        if visitas_to_update:
            db.bulk_update_mappings(models.Visita, visitas_to_update)
        
        if visitas_to_create:
            db.bulk_insert_mappings(models.Visita, visitas_to_create)

        print(f"--- Commit de {total_visitas_procesadas} registros finalizado ---")
        db.commit()
        return total_visitas_procesadas, repetidos_ninos_cnt, nuevos_ninos_cnt
        
    except Exception as e:
        print(f"ERROR FATAL EN EXCEL SERVICE: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise e

def process_excel_async(carga_id: int, file_content: bytes, mes: int, anio: int, user_id: int):
    """Tarea de fondo para procesar el Excel sin bloquear el servidor"""
    logger.info(f"Iniciando tarea asíncrona para carga {carga_id} (Mes: {mes}, Año: {anio})")
    db = SessionLocal()
    try:
        # 1. Actualizar estado a 'procesando'
        carga = db.query(models.CargaExcel).filter(models.CargaExcel.id == carga_id).first()
        if not carga: 
            logger.error(f"No se encontró el registro de carga {carga_id}")
            return
        
        carga.estado = "procesando"
        db.commit()
        
        # 2. Procesar el Excel
        total_visitas, repetidos, nuevos = process_minsa_excel(file_content, db, mes, anio, user_id)
        
        # 3. Actualizar con resultados finales
        carga.estado = "completado"
        carga.total_registros = total_visitas
        carga.total_repetidos = repetidos
        db.commit()
        logger.info(f"Carga {carga_id} completada exitosamente. Total visitas: {total_visitas}")
        
    except Exception as e:
        logger.error(f"Error crítico en carga {carga_id}: {str(e)}")
        traceback.print_exc()
        db.rollback()
        # Registrar el error en la carga
        carga = db.query(models.CargaExcel).filter(models.CargaExcel.id == carga_id).first()
        if carga:
            carga.estado = "error"
            carga.mensaje_error = f"Error en procesamiento: {str(e)[:450]}"
            db.commit()
    finally:
        db.close()
