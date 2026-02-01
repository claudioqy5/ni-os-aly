from fpdf import FPDF
from datetime import datetime
import io

class ChronicHistoryPDF(FPDF):
    def header(self):
        # Logo o Título
        self.set_font('helvetica', 'B', 16)
        self.set_text_color(219, 39, 119) # Rosa marca
        self.cell(0, 10, self.clean_text('FICHA DE HISTORIAL CLÍNICO - NIÑO SANO'), 0, 1, 'C')
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(100)
        self.cell(0, 5, self.clean_text(f'Generado el: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}'), 0, 1, 'R')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Página {self.page_no()}/{{nb}}', 0, 0, 'C')

    def section_title(self, label):
        self.set_font('helvetica', 'B', 12)
        self.set_fill_color(252, 232, 235) # Rosa claro fondo
        self.set_text_color(190, 24, 93) # Rosa oscuro texto
        self.cell(0, 10, self.clean_text(f'  {label}'), 0, 1, 'L', fill=True)
        self.ln(2)

    def table_header(self):
        self.set_font('helvetica', 'B', 9)
        self.set_fill_color(245, 245, 245)
        self.set_text_color(50)
        self.cell(25, 8, 'FECHA', 1, 0, 'C', fill=True)
        self.cell(35, 8, 'ESTADO', 1, 0, 'C', fill=True)
        self.cell(60, 8, 'EESS ATENCION', 1, 0, 'C', fill=True)
        self.cell(70, 8, 'ACTOR SOCIAL', 1, 1, 'C', fill=True)

    def clean_text(self, text):
        if not text: return "---"
        # FPDF2 con fuentes estándar prefiere latin-1. 
        # Esta limpieza evita errores con caracteres unicode raros.
        return str(text).encode('latin-1', 'replace').decode('latin-1')

    def info_row(self, label, value):
        self.set_font('helvetica', 'B', 10)
        self.set_text_color(50)
        self.cell(45, 7, f'{label}:', 0, 0)
        self.set_font('helvetica', '', 10)
        self.set_text_color(0)
        self.cell(0, 7, self.clean_text(value), 0, 1)

def generate_child_history_pdf(nino, visitas):
    pdf = ChronicHistoryPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # --- SECCIÓN: DATOS DEL NIÑO ---
    pdf.section_title('DATOS PERSONALES DEL NIÑO')
    pdf.info_row('DNI / CNV', nino.dni_nino)
    pdf.info_row('NOMBRES', nino.nombres)
    pdf.info_row('FECHA NACIMIENTO', nino.fecha_nacimiento.strftime('%d/%m/%Y') if nino.fecha_nacimiento else '---')
    pdf.info_row('RANGO EDAD', nino.rango_edad)
    pdf.info_row('HISTORIA CLÍNICA', nino.historia_clinica)
    pdf.info_row('DIRECCIÓN', nino.direccion)
    pdf.info_row('ESTABLECIMIENTO', nino.establecimiento_asignado)
    pdf.ln(6)

    # --- SECCIÓN: DATOS FAMILIARES ---
    pdf.section_title('DATOS FAMILIARES / CONTACTO')
    pdf.info_row('DNI MADRE', nino.dni_madre)
    pdf.info_row('NOMBRE MADRE', nino.nombre_madre)
    pdf.info_row('CELULAR MADRE', nino.celular_madre)
    pdf.ln(6)

    # --- SECCIÓN: HISTORIAL DE VISITAS ---
    pdf.section_title('HISTORIAL CRONOLOGICO DE VISITAS')
    
    if not visitas:
        pdf.set_font('helvetica', 'I', 10)
        pdf.cell(0, 10, 'No hay visitas registradas para este nino.', 0, 1)
    else:
        pdf.table_header()
        
        pdf.set_font('helvetica', '', 8)
        pdf.set_text_color(0)
        
        # Ordenar visitas por fecha descendente
        sorted_visitas = sorted(visitas, key=lambda x: x.fecha_visita, reverse=True)
        
        for v in sorted_visitas:
            # Verificar espacio para la fila (aprox 15mm si tiene observación)
            needed_space = 15 if v.observacion else 8
            if pdf.get_y() + needed_space > 270:
                pdf.add_page()
                pdf.table_header()
                pdf.set_font('helvetica', '', 8)

            f_v = v.fecha_visita.strftime('%d/%m/%Y') if v.fecha_visita else '---'
            
            # Fila principal
            pdf.cell(25, 7, pdf.clean_text(f_v), 1, 0, 'C')
            
            estado = (v.estado or '---').capitalize()
            # Color según estado
            if estado == 'Encontrado': pdf.set_text_color(22, 101, 52) # Verde
            elif estado == 'No encontrado': pdf.set_text_color(185, 28, 28) # Rojo
            else: pdf.set_text_color(0)
            
            pdf.cell(35, 7, pdf.clean_text(estado), 1, 0, 'C')
            pdf.set_text_color(0) # Reset
            
            pdf.cell(60, 7, pdf.clean_text((v.establecimiento_atencion or '---')[:35]), 1, 0, 'L')
            pdf.cell(70, 7, pdf.clean_text((v.actor_social or '---')[:40]), 1, 1, 'L')
            
            # Fila de observación (si existe)
            if v.observacion:
                pdf.set_font('helvetica', 'I', 7)
                pdf.set_text_color(80)
                # Dibujar un cuadro que abarque toda la tabla
                pdf.multi_cell(190, 5, pdf.clean_text(f'Observacion: {v.observacion}'), 1, 'L')
                pdf.set_font('helvetica', '', 8)
                pdf.set_text_color(0)
                pdf.ln(1) # Espacio entre visitas

    # Retornar como bytes
    return bytes(pdf.output())
