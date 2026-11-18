"""Servicio principal del establecimiento de salud.

Patrón Singleton: existe una sola instancia de CentroSalud, de modo que todo
el programa trabaja sobre el mismo registro de pacientes y citas.
Las dependencias (seguridad y almacén) se inyectan para poder cambiarlas
o simularlas en las pruebas (inversión de dependencias).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from . import funcional
from .excepciones import (
    AlmacenamientoError,
    CitaDuplicadaError,
    CitaNoEncontradaError,
    DatoInvalidoError,
    PacienteDuplicadoError,
    PacienteNoEncontradoError,
    SistemaRuralError,
)
from .fabrica import FabricaPersonas
from .modelos import ESPECIALIDADES, Cita, EstadoCita, Paciente


class CentroSalud:
    """Agrega pacientes y citas del establecimiento (agregación)."""

    _instancia: "CentroSalud | None" = None

    def __init__(self, seguridad, almacen):
        self._seguridad = seguridad
        self._almacen = almacen
        self._pacientes: dict[str, Paciente] = {}
        self._citas: list[Cita] = []
        self._siguiente_id = 1
        self.cargar()

    @classmethod
    def obtener_instancia(cls, seguridad=None, almacen=None) -> "CentroSalud":
        """Devuelve la única instancia; la primera vez exige las dependencias."""
        if cls._instancia is None:
            if seguridad is None or almacen is None:
                raise SistemaRuralError(
                    "La primera vez se deben indicar la seguridad y el almacén."
                )
            cls._instancia = cls(seguridad, almacen)
        return cls._instancia

    @classmethod
    def reiniciar(cls) -> None:
        """Descarta la instancia actual (se usa en pruebas y al cerrar el programa)."""
        cls._instancia = None

    def registrar_paciente(self, nombre: str, dni: str, fecha_nacimiento: date) -> Paciente:
        dni_hash = self._seguridad.proteger_dni(dni)
        if dni_hash in self._pacientes:
            raise PacienteDuplicadoError("este dni ya esta registrado con un paciente.")
        paciente = FabricaPersonas.crear(
            "paciente", nombre=nombre, dni_hash=dni_hash, fecha_nacimiento=fecha_nacimiento
        )
        self._pacientes[dni_hash] = paciente
        self._persistir()
        return paciente

    def buscar_paciente(self, dni: str) -> Paciente:
        dni_hash = self._seguridad.proteger_dni(dni)
        try:
            return self._pacientes[dni_hash]
        except KeyError:
            raise PacienteNoEncontradoError("No hay un paciente con ese DNI.") from None

    def nombres_pacientes(self) -> list[str]:
        return funcional.nombres_ordenados(self._pacientes.values())

    def nombre_por_hash(self, dni_hash: str) -> str:
        paciente = self._pacientes.get(dni_hash)
        return paciente.nombre if paciente else "(paciente no encontrado)"

    def _validar_cita_duplicada(
        self,
        paciente_hash: str,
        especialidad: str,
        fecha: date,
        excluir_id: int | None = None,
    ) -> None:
        """Comprueba que no exista otra cita programada igual para el paciente."""
        repetida = any(
            cita.id != excluir_id
            and cita.paciente_hash == paciente_hash
            and cita.especialidad == especialidad
            and cita.fecha == fecha
            and cita.estado is EstadoCita.PROGRAMADA
            for cita in self._citas
        )
        if repetida:
            raise CitaDuplicadaError("El paciente ya tiene esa cita programada.")

    def programar_cita(self, dni: str, especialidad: str, fecha: date) -> Cita:
        paciente = self.buscar_paciente(dni)
        if isinstance(fecha, datetime):
            fecha = fecha.date()
        if especialidad not in ESPECIALIDADES:
            raise DatoInvalidoError(
                f"Especialidad no válida. Opciones: {', '.join(ESPECIALIDADES)}."
            )
        if fecha < date.today():
            raise DatoInvalidoError(
                "No se puede programar una cita en una fecha pasada."
            )
        self._validar_cita_duplicada(paciente.dni_hash, especialidad, fecha)
        cita = Cita(self._siguiente_id, paciente.dni_hash, especialidad, fecha)
        self._siguiente_id += 1
        self._citas.append(cita)
        self._persistir()
        return cita

    def obtener_cita(self, id_cita: int) -> Cita:
        for cita in self._citas:
            if cita.id == id_cita:
                return cita
        raise CitaNoEncontradaError(f"No existe la cita número {id_cita}.")

    def reprogramar_cita(self, id_cita: int, nueva_fecha: date) -> Cita:
        cita = self.obtener_cita(id_cita)
        if isinstance(nueva_fecha, datetime):
            nueva_fecha = nueva_fecha.date()
        if nueva_fecha < date.today():
            raise DatoInvalidoError(
                "No se puede reprogramar una cita a una fecha pasada."
            )
        self._validar_cita_duplicada(
            cita.paciente_hash,
            cita.especialidad,
            nueva_fecha,
            excluir_id=cita.id,
        )
        cita.reprogramar(nueva_fecha)
        self._persistir()
        return cita

    def cancelar_cita(self, id_cita: int) -> Cita:
        cita = self.obtener_cita(id_cita)
        cita.cancelar()
        self._persistir()
        return cita

    def registrar_atencion(
        self, id_cita: int, motivo: str, observaciones: str, fecha: date | None = None
    ) -> Cita:
        cita = self.obtener_cita(id_cita)
        cita.registrar_atencion(motivo, observaciones, fecha or date.today())
        self._persistir()
        return cita

    def citas_pendientes(
        self,
        especialidad: str | None = None,
        desde: date | None = None,
        hasta: date | None = None,
    ) -> list[Cita]:
        """Citas programadas, con filtros opcionales (consulta funcional)."""
        return funcional.filtrar_citas(
            self._citas,
            funcional.es_pendiente,
            funcional.crear_filtro(especialidad, desde, hasta),
        )

    def reporte_semanal(self, inicio: date) -> dict:
        """Atenciones realizadas en los 7 días desde ``inicio``, por especialidad."""
        if isinstance(inicio, datetime):
            inicio = inicio.date()
        fin = inicio + timedelta(days=6)
        atendidas = [
            cita
            for cita in self._citas
            if cita.estado is EstadoCita.ATENDIDA
            and cita.atencion is not None
            and inicio <= cita.atencion.fecha <= fin
        ]
        por_especialidad = funcional.contar_por_especialidad(atendidas)
        return {
            "inicio": inicio,
            "fin": fin,
            "atenciones_por_especialidad": por_especialidad,
            "total": sum(por_especialidad.values()),
        }

    def guardar(self) -> None:
        self._almacen.guardar(
            {
                "siguiente_id": self._siguiente_id,
                "pacientes": [p.a_dict() for p in self._pacientes.values()],
                "citas": [c.a_dict() for c in self._citas],
            }
        )

    def _persistir(self) -> None:
        """Guarda los cambios; si falla, restaura el estado que sigue en disco."""
        try:
            self.guardar()
        except SistemaRuralError:
            try:
                self.cargar()
            except SistemaRuralError:
                pass
            raise

    def cargar(self) -> None:
        datos = self._almacen.cargar()
        try:
            pacientes = [Paciente.desde_dict(d) for d in datos.get("pacientes", [])]
            self._pacientes = {p.dni_hash: p for p in pacientes}
            self._citas = [Cita.desde_dict(d) for d in datos.get("citas", [])]
            guardado = datos.get("siguiente_id", 0)
            if not isinstance(guardado, int) or isinstance(guardado, bool):
                raise AlmacenamientoError(
                    "El campo 'siguiente_id' no es un número entero."
                )
            ids = [cita.id for cita in self._citas]
            self._siguiente_id = max(guardado, max(ids, default=0) + 1)
        except SistemaRuralError:
            raise
        except (KeyError, TypeError, ValueError) as error:
            raise AlmacenamientoError(
                f"Los datos guardados están incompletos o dañados: {error}"
            ) from error

    @property
    def total_citas(self) -> int:
        return len(self._citas)

    def cantidad_por_estado(self, estado: EstadoCita) -> int:
        return len(list(filter(lambda c: c.estado is estado, self._citas)))
