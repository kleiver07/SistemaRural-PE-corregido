"""Interfaz de consola para el personal del establecimiento.

Cada opción del menú se asocia a un método manejador mediante un diccionario
(enfoque orientado a eventos: la acción del usuario dispara su manejador).
La entrada y la salida se inyectan para poder probar la interfaz sin teclado.
"""
from __future__ import annotations

import re
from datetime import date

from .centro_salud import CentroSalud
from .excepciones import DatoInvalidoError, SistemaRuralError
from .modelos import ESPECIALIDADES

MENU = """
=== Centro de salud rural ===
1. Registrar paciente
2. Programar cita
3. Ver citas pendientes
4. Registrar atención
5. Cancelar cita
6. Reporte semanal
0. Salir
"""

FORMATOS_FECHA = "AAAA-MM-DD, DD/MM/AAAA, DD-MM-AAAA o DD MM AAAA"


def parsear_fecha(texto: str) -> date:
    """Convierte una fecha escrita de forma flexible en un ``date``.

    Acepta ``2008-02-02``, ``02/02/2008``, ``02-02-2008``, ``02.02.2008``
    y ``02 02 2008``. El año debe tener cuatro dígitos.
    """
    texto = texto.strip()
    if not texto:
        raise DatoInvalidoError("La fecha no puede estar vacía.")

    # Formato ISO (AAAA-MM-DD), que es el que se guarda en el JSON.
    try:
        return date.fromisoformat(texto)
    except ValueError:
        pass

    partes = re.split(r"[\s/.-]+", texto)
    if len(partes) == 3 and all(p.isascii() and p.isdigit() for p in partes):
        if len(partes[0]) == 4:
            anio, mes, dia = (int(p) for p in partes)
        elif len(partes[2]) == 4:
            dia, mes, anio = (int(p) for p in partes)
        else:
            anio = mes = dia = 0
        try:
            return date(anio, mes, dia)
        except ValueError:
            pass

    raise DatoInvalidoError(f"Fecha inválida. Use {FORMATOS_FECHA}.")


class InterfazConsola:
    def __init__(self, centro: CentroSalud, entrada=input, salida=print):
        self._centro = centro
        self._entrada = entrada
        self._salida = salida
        self._manejadores = {
            "1": self._registrar_paciente,
            "2": self._programar_cita,
            "3": self._ver_pendientes,
            "4": self._registrar_atencion,
            "5": self._cancelar_cita,
            "6": self._reporte_semanal,
        }

    # ---------- Utilidades de entrada ----------
    def _pedir(self, mensaje: str) -> str:
        return self._entrada(f"{mensaje}: ").strip()

    def _pedir_fecha(self, mensaje: str) -> date:
        texto = self._pedir(f"{mensaje} (DD/MM/AAAA)")
        return parsear_fecha(texto)

    def _pedir_entero(self, mensaje: str) -> int:
        texto = self._pedir(mensaje)
        if not texto.isdigit():
            raise DatoInvalidoError("Debe ingresar un número entero.")
        return int(texto)

    def _pedir_especialidad(self) -> str:
        for numero, nombre in enumerate(ESPECIALIDADES, start=1):
            self._salida(f"  {numero}. {nombre}")
        indice = self._pedir_entero("Especialidad (número)")
        if not 1 <= indice <= len(ESPECIALIDADES):
            raise DatoInvalidoError("Número de especialidad fuera de rango.")
        return ESPECIALIDADES[indice - 1]

    # ---------- Manejadores de cada opción ----------
    def _registrar_paciente(self) -> None:
        nombre = self._pedir("Nombre completo")
        dni = self._pedir("DNI (8 dígitos)")
        nacimiento = self._pedir_fecha("Fecha de nacimiento")
        paciente = self._centro.registrar_paciente(nombre, dni, nacimiento)
        self._salida(f"Paciente registrado: {paciente.descripcion()}")

    def _programar_cita(self) -> None:
        dni = self._pedir("DNI del paciente")
        especialidad = self._pedir_especialidad()
        fecha = self._pedir_fecha("Fecha de la cita")
        cita = self._centro.programar_cita(dni, especialidad, fecha)
        self._salida(f"Cita N.° {cita.id} programada para el {cita.fecha}.")

    def _ver_pendientes(self) -> None:
        pendientes = self._centro.citas_pendientes()
        if not pendientes:
            self._salida("No hay citas pendientes.")
        for cita in sorted(pendientes, key=lambda c: c.fecha):
            nombre = self._centro.nombre_por_hash(cita.paciente_hash)
            self._salida(f"N.° {cita.id} | {cita.fecha} | {cita.especialidad} | {nombre}")

    def _registrar_atencion(self) -> None:
        id_cita = self._pedir_entero("N.° de cita")
        motivo = self._pedir("Motivo de consulta")
        observaciones = self._pedir("Observaciones")
        self._centro.registrar_atencion(id_cita, motivo, observaciones)
        self._salida(f"Atención registrada para la cita N.° {id_cita}.")

    def _cancelar_cita(self) -> None:
        id_cita = self._pedir_entero("N.° de cita")
        self._centro.cancelar_cita(id_cita)
        self._salida(f"Cita N.° {id_cita} cancelada.")

    def _reporte_semanal(self) -> None:
        inicio = self._pedir_fecha("Primer día de la semana")
        reporte = self._centro.reporte_semanal(inicio)
        self._salida(f"Atenciones del {reporte['inicio']} al {reporte['fin']}:")
        for especialidad, cantidad in reporte["atenciones_por_especialidad"].items():
            self._salida(f"  {especialidad}: {cantidad}")
        self._salida(f"  Total: {reporte['total']}")

    # ---------- Bucle principal ----------
    def ejecutar(self) -> None:
        try:
            while True:
                self._salida(MENU)
                opcion = self._pedir("Elija una opción")
                if opcion == "0":
                    self._salida("Hasta pronto.")
                    return
                manejador = self._manejadores.get(opcion)
                if manejador is None:
                    self._salida("Opción no válida.")
                    continue
                try:
                    manejador()
                except SistemaRuralError as error:
                    # Error esperado del negocio: se informa y el programa continúa.
                    self._salida(f"No se pudo completar la operación: {error}")
        except (EOFError, KeyboardInterrupt):
            self._salida("\nHasta pronto.")
