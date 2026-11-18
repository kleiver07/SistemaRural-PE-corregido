"""Modelo de dominio (paradigma orientado a objetos).

Relaciones principales:
- Herencia: Paciente y PersonalSalud heredan de Persona (clase abstracta).
- Polimorfismo: cada subclase implementa ``descripcion()`` a su manera.
- Composición: una Cita contiene su Atencion (no existe sin la cita).
- Encapsulamiento: atributos privados con propiedades y validación.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime
from enum import Enum

from .excepciones import DatoInvalidoError, EstadoCitaInvalidoError

ESPECIALIDADES = (
    "Medicina General",
    "Obstetricia",
    "Pediatría",
    "Odontología",
    "Enfermería",
)


class EstadoCita(Enum):
    """Estados posibles de una cita."""

    PROGRAMADA = "programada"
    ATENDIDA = "atendida"
    CANCELADA = "cancelada"


def _texto_no_vacio(valor, campo: str) -> str:
    """Valida que ``valor`` sea un texto con contenido y lo devuelve sin espacios."""
    if not isinstance(valor, str) or not valor.strip():
        raise DatoInvalidoError(f"El campo '{campo}' no puede estar vacío.")
    return valor.strip()


def _validar_fecha(valor, campo: str) -> date:
    # ``datetime`` es subclase de ``date``: se normaliza para no guardar horas
    # que después no se pueden reconstruir con ``date.fromisoformat``.
    if isinstance(valor, datetime):
        valor = valor.date()
    if type(valor) is not date:
        raise DatoInvalidoError(f"El campo '{campo}' debe ser una fecha válida.")
    return valor


class Persona(ABC):
    """Clase base abstracta para las personas del sistema."""

    def __init__(self, nombre: str):
        self.nombre = nombre  # pasa por el setter con validación

    @property
    def nombre(self) -> str:
        return self.__nombre

    @nombre.setter
    def nombre(self, valor: str) -> None:
        self.__nombre = _texto_no_vacio(valor, "nombre")

    @abstractmethod
    def descripcion(self) -> str:
        """Texto corto que describe a la persona (polimorfismo)."""


class Paciente(Persona):
    """Paciente del establecimiento. Su DNI solo existe como hash."""

    def __init__(self, nombre: str, dni_hash: str, fecha_nacimiento: date):
        super().__init__(nombre)
        self.__dni_hash = _texto_no_vacio(dni_hash, "dni_hash")
        self.fecha_nacimiento = fecha_nacimiento

    @property
    def dni_hash(self) -> str:
        """Solo lectura: el hash del DNI no se puede reemplazar."""
        return self.__dni_hash

    @property
    def fecha_nacimiento(self) -> date:
        return self.__fecha_nacimiento

    @fecha_nacimiento.setter
    def fecha_nacimiento(self, valor: date) -> None:
        valor = _validar_fecha(valor, "fecha_nacimiento")
        if valor > date.today():
            raise DatoInvalidoError("La fecha de nacimiento no puede ser futura.")
        self.__fecha_nacimiento = valor

    def edad(self, hoy: date | None = None) -> int:
        """Edad en años cumplidos a la fecha ``hoy`` (por defecto, hoy)."""
        hoy = hoy or date.today()
        nacio = self.fecha_nacimiento
        antes_de_cumplir = (hoy.month, hoy.day) < (nacio.month, nacio.day)
        return hoy.year - nacio.year - int(antes_de_cumplir)

    def descripcion(self) -> str:
        return f"Paciente {self.nombre} ({self.edad()} años)"

    def a_dict(self) -> dict:
        return {
            "nombre": self.nombre,
            "dni_hash": self.dni_hash,
            "fecha_nacimiento": self.fecha_nacimiento.isoformat(),
        }

    @classmethod
    def desde_dict(cls, datos: dict) -> "Paciente":
        return cls(
            datos["nombre"],
            datos["dni_hash"],
            date.fromisoformat(datos["fecha_nacimiento"]),
        )


class PersonalSalud(Persona):
    """Profesional del establecimiento (obstetra, enfermera, técnico, etc.)."""

    def __init__(self, nombre: str, cargo: str):
        super().__init__(nombre)
        self.cargo = cargo

    @property
    def cargo(self) -> str:
        return self.__cargo

    @cargo.setter
    def cargo(self, valor: str) -> None:
        self.__cargo = _texto_no_vacio(valor, "cargo")

    def descripcion(self) -> str:
        return f"{self.cargo} {self.nombre}"


class Atencion:
    """Registro clínico de una cita atendida (parte de la Cita: composición)."""

    def __init__(self, motivo: str, observaciones: str, fecha: date):
        self.__motivo = _texto_no_vacio(motivo, "motivo")
        self.__observaciones = _texto_no_vacio(observaciones, "observaciones")
        self.__fecha = _validar_fecha(fecha, "fecha de atención")

    @property
    def motivo(self) -> str:
        return self.__motivo

    @property
    def observaciones(self) -> str:
        return self.__observaciones

    @property
    def fecha(self) -> date:
        return self.__fecha

    def a_dict(self) -> dict:
        return {
            "motivo": self.motivo,
            "observaciones": self.observaciones,
            "fecha": self.fecha.isoformat(),
        }

    @classmethod
    def desde_dict(cls, datos: dict) -> "Atencion":
        return cls(datos["motivo"], datos["observaciones"], date.fromisoformat(datos["fecha"]))


class Cita:
    """Cita médica de un paciente (se vincula por el hash de su DNI)."""

    def __init__(self, id_cita: int, paciente_hash: str, especialidad: str, fecha: date):
        if (
            not isinstance(id_cita, int)
            or isinstance(id_cita, bool)
            or id_cita < 1
        ):
            raise DatoInvalidoError("El id de la cita debe ser un entero positivo.")
        if especialidad not in ESPECIALIDADES:
            raise DatoInvalidoError(
                f"Especialidad no válida. Opciones: {', '.join(ESPECIALIDADES)}."
            )
        self.__id = id_cita
        self.__paciente_hash = _texto_no_vacio(paciente_hash, "paciente_hash")
        self.__especialidad = especialidad
        self.__fecha = _validar_fecha(fecha, "fecha de cita")
        self.__estado = EstadoCita.PROGRAMADA
        self.__atencion: Atencion | None = None

    @property
    def id(self) -> int:
        return self.__id

    @property
    def paciente_hash(self) -> str:
        return self.__paciente_hash

    @property
    def especialidad(self) -> str:
        return self.__especialidad

    @property
    def fecha(self) -> date:
        return self.__fecha

    @property
    def estado(self) -> EstadoCita:
        return self.__estado

    @property
    def atencion(self) -> Atencion | None:
        return self.__atencion

    def _exigir_programada(self, accion: str) -> None:
        if self.__estado is not EstadoCita.PROGRAMADA:
            raise EstadoCitaInvalidoError(
                f"No se puede {accion} una cita en estado '{self.__estado.value}'."
            )

    def reprogramar(self, nueva_fecha: date) -> None:
        self._exigir_programada("reprogramar")
        self.__fecha = _validar_fecha(nueva_fecha, "fecha de cita")

    def cancelar(self) -> None:
        self._exigir_programada("cancelar")
        self.__estado = EstadoCita.CANCELADA

    def registrar_atencion(self, motivo: str, observaciones: str, fecha: date) -> None:
        self._exigir_programada("atender")
        fecha = _validar_fecha(fecha, "fecha de atención")
        if fecha > date.today():
            raise DatoInvalidoError("La fecha de atención no puede ser futura.")
        self.__atencion = Atencion(motivo, observaciones, fecha)
        self.__estado = EstadoCita.ATENDIDA

    def a_dict(self) -> dict:
        return {
            "id": self.id,
            "paciente_hash": self.paciente_hash,
            "especialidad": self.especialidad,
            "fecha": self.fecha.isoformat(),
            "estado": self.estado.value,
            "atencion": self.atencion.a_dict() if self.atencion else None,
        }

    @classmethod
    def desde_dict(cls, datos: dict) -> "Cita":
        cita = cls(
            datos["id"],
            datos["paciente_hash"],
            datos["especialidad"],
            date.fromisoformat(datos["fecha"]),
        )
        # Se restaura el estado guardado respetando las reglas del modelo.
        try:
            estado = EstadoCita(datos["estado"])
        except (KeyError, ValueError) as error:
            raise DatoInvalidoError(
                f"Estado de cita inválido: {datos.get('estado')!r}."
            ) from error
        if estado is EstadoCita.ATENDIDA:
            if not datos.get("atencion"):
                raise DatoInvalidoError(
                    f"La cita {cita.id} figura como atendida pero no tiene "
                    "datos de atención."
                )
            atencion = Atencion.desde_dict(datos["atencion"])
            cita.registrar_atencion(atencion.motivo, atencion.observaciones, atencion.fecha)
        elif estado is EstadoCita.CANCELADA:
            cita.cancelar()
        return cita
