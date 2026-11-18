from datetime import date, timedelta

import pytest

from sistemarural.centro_salud import CentroSalud
from sistemarural.almacen import AlmacenJSON
from sistemarural.excepciones import (
    CitaDuplicadaError,
    DatoInvalidoError,
    PacienteDuplicadoError,
    PacienteNoEncontradoError,
    SistemaRuralError,
)
from sistemarural.modelos import ESPECIALIDADES, EstadoCita
from sistemarural.seguridad import GestorSeguridad


@pytest.fixture
def centro(tmp_path):
    return CentroSalud(
        GestorSeguridad(tmp_path / "sal.bin", iteraciones=1),
        AlmacenJSON(tmp_path / "centro.json"),
    )


def test_registrar_y_buscar_paciente(centro):
    paciente = centro.registrar_paciente("María", "12345678", date(1990, 1, 1))

    assert centro.buscar_paciente("12345678") is paciente
    assert centro.nombres_pacientes() == ["María"]
    assert centro.nombre_por_hash(paciente.dni_hash) == "María"
    assert "12345678" not in paciente.dni_hash


def test_no_permite_paciente_duplicado_ni_busqueda_inexistente(centro):
    centro.registrar_paciente("María", "12345678", date(1990, 1, 1))

    with pytest.raises(PacienteDuplicadoError):
        centro.registrar_paciente("Otra", "12345678", date(1991, 1, 1))
    with pytest.raises(PacienteNoEncontradoError):
        centro.buscar_paciente("87654321")


def test_programa_cita_y_persiste_datos(centro, tmp_path):
    fecha = date.today() + timedelta(days=3)
    centro.registrar_paciente("María", "12345678", date(1990, 1, 1))
    cita = centro.programar_cita("12345678", ESPECIALIDADES[0], fecha)

    recargado = CentroSalud(
        GestorSeguridad(tmp_path / "sal.bin", iteraciones=1),
        AlmacenJSON(tmp_path / "centro.json"),
    )
    assert cita.id == 1
    assert recargado.total_citas == 1
    assert recargado.obtener_cita(1).fecha == fecha


def test_rechaza_cita_pasada_especialidad_invalida_y_duplicada(centro):
    centro.registrar_paciente("María", "12345678", date(1990, 1, 1))
    fecha = date.today() + timedelta(days=3)
    centro.programar_cita("12345678", ESPECIALIDADES[0], fecha)

    with pytest.raises(CitaDuplicadaError):
        centro.programar_cita("12345678", ESPECIALIDADES[0], fecha)
    with pytest.raises(DatoInvalidoError):
        centro.programar_cita("12345678", ESPECIALIDADES[0], date.today() - timedelta(days=1))
    with pytest.raises(DatoInvalidoError):
        centro.programar_cita("12345678", "No existe", fecha)


def test_reprograma_cancela_y_filtra_citas_pendientes(centro):
    centro.registrar_paciente("María", "12345678", date(1990, 1, 1))
    fecha = date.today() + timedelta(days=3)
    cita = centro.programar_cita("12345678", ESPECIALIDADES[0], fecha)
    nueva_fecha = fecha + timedelta(days=2)

    centro.reprogramar_cita(cita.id, nueva_fecha)
    assert centro.citas_pendientes(especialidad=ESPECIALIDADES[0], desde=nueva_fecha) == [cita]

    centro.cancelar_cita(cita.id)
    assert cita.estado is EstadoCita.CANCELADA
    assert centro.citas_pendientes() == []


def test_registra_atencion_y_reporte_semanal(centro):
    centro.registrar_paciente("María", "12345678", date(1990, 1, 1))
    cita = centro.programar_cita("12345678", ESPECIALIDADES[0], date.today())
    centro.registrar_atencion(cita.id, "Control", "Estable", date.today())

    reporte = centro.reporte_semanal(date.today())
    assert cita.estado is EstadoCita.ATENDIDA
    assert reporte["total"] == 1
    assert reporte["atenciones_por_especialidad"] == {ESPECIALIDADES[0]: 1}
    assert centro.cantidad_por_estado(EstadoCita.ATENDIDA) == 1


def test_singleton_exige_dependencias_y_reutiliza_instancia(centro):
    CentroSalud.reiniciar()
    with pytest.raises(SistemaRuralError):
        CentroSalud.obtener_instancia()

    instancia = CentroSalud.obtener_instancia(centro._seguridad, centro._almacen)
    assert CentroSalud.obtener_instancia() is instancia
    CentroSalud.reiniciar()
