from app.services.pdf_service import generate_child_history_pdf
from datetime import date

class MockNino:
    def __init__(self):
        self.dni_nino = "12345678"
        self.nombres = "NIÑO PRUEBA"
        self.fecha_nacimiento = date(2020, 1, 1)
        self.rango_edad = "4 AÑOS"
        self.historia_clinica = "HC-001"
        self.direccion = "CALLE FALSA 123"
        self.establecimiento_asignado = "EESS PRUEBA"
        self.dni_madre = "87654321"
        self.nombre_madre = "MADRE PRUEBA"
        self.celular_madre = "987654321"

class MockVisita:
    def __init__(self, fecha):
        self.fecha_visita = fecha
        self.estado = "encontrado"
        self.establecimiento_atencion = "EESS ATENCION"
        self.actor_social = "ACTOR SOCIAL"
        self.observacion = "OBSERVACION DE PRUEBA"

def test():
    nino = MockNino()
    visitas = [MockVisita(date(2023, 10, 1)), MockVisita(date(2023, 11, 1))]
    try:
        print("Generando PDF...")
        content = generate_child_history_pdf(nino, visitas)
        print(f"PDF generado con éxito. Tamaño: {len(content)} bytes")
        with open("test_output.pdf", "wb") as f:
            f.write(content)
        print("Archivo test_output.pdf guardado.")
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test()
