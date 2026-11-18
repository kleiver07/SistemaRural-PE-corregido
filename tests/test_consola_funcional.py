from datetime import date, timedelta

import pytest

from sistemarural.consola import InterfazConsola, parsear_fecha
from sistemarural.excepciones import DatoInvalidoError
from sistemarural.fabrica import FabricaPersonas
from sistemarural.funcional import contar_por_especialidad, crear_filtro, filtrar_citas, nombres_ordenados
from sistemarural.modelos import Cita, ESPECIALIDADES, EstadoCita, Paciente


@pytest.mark.parametrize(
    "texto,esperada",
    [
        ("2024-02-02", date(2024, 2, 2)),
        ("02/02/2024", date(2024, 2, 2)),
        ("02-02-2024", date(2024, 2, 2)),
        ("02.02.2024", date(2024, 2, 2)),
        ("02 02 2024", date(2024, 2, 2)),
    ],
)
def test_parsear_fecha_acepta_formatos_validos(texto, esperada):
    assert parsear_fecha(texto) == esperada


@pytest.mark.parametrize("texto", ["", "31/02/2024", "02/02/24", "mañana"])
def test_parsear_fecha_rechaza_formatos_invalidos(texto):
    with pytest.raises(DatoInvalidoError):
        parsear_fecha(texto)


def test_fabrica_crea_personas_y_rechaza_tipo_desconocido():
    paciente = FabricaPersonas.crear(
        "paciente", nombre="Ana", dni_hash="hash", fecha_nacimiento=date(2000, 1, 1)
    )
    personal = FabricaPersonas.crear("personal", nombre="Luis", cargo="Enfermero")

    assert paciente.nombre == "Ana"
    assert personal.descripcion() == "Enfermero Luis"
    with pytest.raises(DatoInvalidoError):
        FabricaPersonas.crear("desconocido")
    with pytest.raises(DatoInvalidoError, match="Falta el dato"):
        FabricaPersonas.crear("personal", nombre="Luis")


def test_consultas_funcionales_filtran_y_agrupan():
    hoy = date.today()
    citas = [
        Cita(1, "a", ESPECIALIDADES[0], hoy),
        Cita(2, "b", ESPECIALIDADES[1], hoy + timedelta(days=1)),
    ]
    citas[1].registrar_atencion("Control", "Bien", hoy)
    resultado = filtrar_citas(citas, lambda cita: cita.estado is EstadoCita.PROGRAMADA,
                              crear_filtro(ESPECIALIDADES[0], hoy, hoy))

    assert resultado == [citas[0]]
    assert contar_por_especialidad(citas) == {ESPECIALIDADES[0]: 1, ESPECIALIDADES[1]: 1}
    assert nombres_ordenados([
        Paciente("Zoe", "z", date(2000, 1, 1)),
        Paciente("Ana", "a", date(2000, 1, 1)),
    ]) == ["Ana", "Zoe"]


def test_interfaz_muestra_opcion_invalida_y_sale():
    respuestas = iter(["9", "0"])
    mensajes = []
    interfaz = InterfazConsola(object(), entrada=lambda _prompt: next(respuestas), salida=mensajes.append)

    interfaz.ejecutar()

    assert any("Opción no válida" in mensaje for mensaje in mensajes)
    assert mensajes[-1] == "Hasta pronto."
