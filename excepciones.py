"""Excepciones propias del sistema.

Una jerarquía propia permite capturar los errores del negocio sin esconder
errores de programación (por ejemplo, un TypeError inesperado).
"""


class SistemaRuralError(Exception):
    """Error base de SistemaRural-PE."""


class DatoInvalidoError(SistemaRuralError, ValueError):
    """Un dato de entrada no cumple las reglas de validación."""


class PacienteDuplicadoError(SistemaRuralError):
    """Ya existe un paciente registrado con ese DNI."""


class PacienteNoEncontradoError(SistemaRuralError):
    """No existe un paciente con el DNI indicado."""


class CitaDuplicadaError(SistemaRuralError):
    """El paciente ya tiene una cita programada igual."""


class CitaNoEncontradaError(SistemaRuralError):
    """No existe una cita con el identificador indicado."""


class EstadoCitaInvalidoError(SistemaRuralError):
    """La operación no es válida para el estado actual de la cita."""


class AlmacenamientoError(SistemaRuralError):
    """No se pudo leer o escribir el archivo de datos."""

