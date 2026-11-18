"""Persistencia local en un archivo JSON (el sistema funciona sin conexión)."""
import json
import os
import tempfile
from pathlib import Path

from .excepciones import AlmacenamientoError


class AlmacenJSON:
    """Lee y escribe un diccionario en un archivo JSON de forma segura."""

    def __init__(self, ruta):
        self._ruta = Path(ruta)

    def cargar(self) -> dict:
        """Devuelve los datos guardados o un diccionario vacío si aún no hay archivo."""
        if not self._ruta.exists():
            return {}
        try:
            with open(self._ruta, "r", encoding="utf-8") as archivo:
                datos = json.load(archivo)
        except json.JSONDecodeError as error:
            raise AlmacenamientoError(f"El archivo de datos está dañado: {error}") from error
        except OSError as error:
            raise AlmacenamientoError(f"No se pudo leer el archivo de datos: {error}") from error
        if not isinstance(datos, dict):
            raise AlmacenamientoError("El archivo de datos no tiene el formato esperado.")
        return datos

    def guardar(self, datos: dict) -> None:
        """Escribe en un archivo temporal y lo reemplaza, para no dejar datos a medias."""
        try:
            self._ruta.parent.mkdir(parents=True, exist_ok=True)
            descriptor, ruta_temporal = tempfile.mkstemp(
                dir=self._ruta.parent, suffix=".tmp"
            )
        except OSError as error:
            raise AlmacenamientoError(
                f"No se pudo guardar el archivo de datos: {error}"
            ) from error

        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as archivo:
                json.dump(datos, archivo, ensure_ascii=False, indent=2)
            os.replace(ruta_temporal, self._ruta)
        except (OSError, TypeError, ValueError) as error:
            raise AlmacenamientoError(
                f"No se pudo guardar el archivo de datos: {error}"
            ) from error
        finally:
            try:
                Path(ruta_temporal).unlink(missing_ok=True)
            except OSError:
                pass
