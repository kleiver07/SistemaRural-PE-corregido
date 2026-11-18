from datetime import date, datetime, timedelta

import pytest

from sistemarural.excepciones import DatoInvalidoError, EstadoCitaInvalidoError
from sistemarural.modelos import (
    ESPECIALIDADES,
    Atencion,
    Cita,
    EstadoCita,
    Paciente,
    PersonalSalud,
)
from sistemarural.seguridad import GestorSeguridad, validar_dni


def test_validar_dni_acepta_o_elimina_espacios():
    assert validar_dni(" 00123456 ") == "00123456"


@pytest.mark.parametrize("dni", ["123", "123456789", "１２３４５６７８", "12a45678", None])
def test_validar_dni_rechaza_formatos_invalidos(dni):
    with pytest.raises(DatoInvalidoError):
        validar_dni(dni)


def test_gestor_seguridad_persiste_sal_y_compara_hash(tmp_path):
    ruta = tmp_path / "sal.bin"
    primero = GestorSeguridad(ruta, iteraciones=1)
    hash_dni = primero.proteger_dni("12345678")
    segundo = GestorSeguridad(ruta, iteraciones=1)

    assert len(ruta.read_bytes()) == 16
    assert segundo.proteger_dni("12345678") == hash_dni
    assert segundo.coincide("12345678", hash_dni)
    assert not segundo.coincide("87654321", hash_dni)


def test_gestor_seguridad_rechaza_archivo_de_sal_danado(tmp_path):
    ruta = tmp_path / "sal.bin"
    ruta.write_bytes(b"corta")

    from sistemarural.excepciones import AlmacenamientoError

    with pytest.raises(AlmacenamientoError, match="sal está dañado"):
        GestorSeguridad(ruta, iteraciones=1)


def test_paciente_valida_fecha_y_calcula_edad():
    paciente = Paciente("  Ana Pérez ", "hash-dni", date(2000, 6, 15))

    assert paciente.nombre == "Ana Pérez"
    assert paciente.edad(date(2024, 6, 14)) == 23
    assert paciente.edad(date(2024, 6, 15)) == 24
    assert Paciente.desde_dict(paciente.a_dict()).a_dict() == paciente.a_dict()


def test_paciente_rechaza_nacimiento_futuro_y_nombre_vacio():
    with pytest.raises(DatoInvalidoError):
        Paciente("Ana", "hash", date.today() + timedelta(days=1))
    with pytest.raises(DatoInvalidoError):
        Paciente("  ", "hash", date(2000, 1, 1))


def test_fecha_datetime_se_normaliza_a_date():
    paciente = Paciente("Ana", "hash", datetime(2000, 1, 1, 12, 30))

    assert paciente.fecha_nacimiento == date(2000, 1, 1)


def test_personal_salud_descripcion():
    personal = PersonalSalud("Luis", "Enfermero")

    assert personal.descripcion() == "Enfermero Luis"


def test_cita_cambia_estado_y_rechaza_operaciones_despues_de_cancelar():
    cita = Cita(1, "hash", ESPECIALIDADES[0], date.today())
    cita.cancelar()

    assert cita.estado is EstadoCita.CANCELADA
    with pytest.raises(EstadoCitaInvalidoError):
        cita.cancelar()
    with pytest.raises(EstadoCitaInvalidoError):
        cita.reprogramar(date.today() + timedelta(days=2))


def test_cita_registra_atencion_y_se_reconstruye():
    cita = Cita(1, "hash", ESPECIALIDADES[0], date.today())
    cita.registrar_atencion("Control", "Sin novedades", date.today())

    reconstruida = Cita.desde_dict(cita.a_dict())
    assert reconstruida.estado is EstadoCita.ATENDIDA
    assert reconstruida.atencion.motivo == "Control"
    assert reconstruida.atencion.observaciones == "Sin novedades"


def test_cita_rechaza_id_y_especialidad_invalidos():
    with pytest.raises(DatoInvalidoError):
        Cita(True, "hash", ESPECIALIDADES[0], date.today())
    with pytest.raises(DatoInvalidoError):
        Cita(1, "hash", "Especialidad desconocida", date.today())


def test_atencion_rechaza_datos_vacios():
    with pytest.raises(DatoInvalidoError):
        Atencion("", "Observación", date.today())
