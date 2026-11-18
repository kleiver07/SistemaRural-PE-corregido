"""Consultas y reportes (paradigma funcional).

Son funciones puras: no modifican sus entradas ni guardan estado, por lo que
son fáciles de probar. Usan funciones de orden superior (filter, map, reduce)
y funciones que devuelven otras funciones (``crear_filtro``).
"""
from __future__ import annotations

from datetime import date, datetime
from functools import reduce
from typing import Callable, Iterable

from .modelos import Cita, EstadoCita, Paciente

Predicado = Callable[[Cita], bool]


def es_pendiente(cita: Cita) -> bool:
    return cita.estado is EstadoCita.PROGRAMADA


def es_atendida(cita: Cita) -> bool:
    return cita.estado is EstadoCita.ATENDIDA


def crear_filtro(
    especialidad: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
) -> Predicado:
    """Función de orden superior: devuelve un predicado según los criterios dados."""
    if isinstance(desde, datetime):
        desde = desde.date()
    if isinstance(hasta, datetime):
        hasta = hasta.date()

    def predicado(cita: Cita) -> bool:
        if especialidad is not None and cita.especialidad != especialidad:
            return False
        if desde is not None and cita.fecha < desde:
            return False
        if hasta is not None and cita.fecha > hasta:
            return False
        return True

    return predicado


def filtrar_citas(citas: Iterable[Cita], *predicados: Predicado) -> list[Cita]:
    """Aplica ``filter`` con una lambda que exige cumplir todos los predicados."""
    return list(filter(lambda cita: all(p(cita) for p in predicados), citas))


def _acumular_conteo(acumulado: dict, especialidad: str) -> dict:
    """Paso de ``reduce``: devuelve un nuevo diccionario sin mutar el anterior."""
    return {**acumulado, especialidad: acumulado.get(especialidad, 0) + 1}


def contar_por_especialidad(citas: Iterable[Cita]) -> dict:
    """Cuenta citas por especialidad usando ``map`` y ``reduce``."""
    especialidades = map(lambda cita: cita.especialidad, citas)
    return reduce(_acumular_conteo, especialidades, {})


def nombres_ordenados(pacientes: Iterable[Paciente]) -> list[str]:
    """Lista de nombres en orden alfabético usando ``map``."""
    return sorted(map(lambda paciente: paciente.nombre, pacientes))
