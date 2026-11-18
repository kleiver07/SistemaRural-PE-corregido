"""Patrón Factory: centraliza la creación de personas del sistema.

Para agregar un nuevo tipo de persona basta registrar un creador en
``_CREADORES``; el resto del código no cambia (principio abierto/cerrado).
"""
from __future__ import annotations

from .excepciones import DatoInvalidoError
from .modelos import Paciente, Persona, PersonalSalud


def _crear_paciente(**datos) -> Paciente:
    return Paciente(datos["nombre"], datos["dni_hash"], datos["fecha_nacimiento"])


def _crear_personal(**datos) -> PersonalSalud:
    return PersonalSalud(datos["nombre"], datos["cargo"])


class FabricaPersonas:
    """Crea instancias de Persona según un tipo textual."""

    _CREADORES = {
        "paciente": _crear_paciente,
        "personal": _crear_personal,
    }

    @classmethod
    def crear(cls, tipo: str, **datos) -> Persona:
        creador = cls._CREADORES.get(tipo)
        if creador is None:
            opciones = ", ".join(sorted(cls._CREADORES))
            raise DatoInvalidoError(f"Tipo de persona desconocido '{tipo}'. Opciones: {opciones}.")
        try:
            return creador(**datos)
        except KeyError as faltante:
            raise DatoInvalidoError(f"Falta el dato requerido: {faltante}.") from faltante
