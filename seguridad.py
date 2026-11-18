"""Protección de datos personales (Ley N.° 29733).

El DNI nunca se guarda ni se muestra en texto plano: solo se conserva un
hash PBKDF2-HMAC-SHA256 calculado con una sal aleatoria que se genera una
sola vez y se guarda en un archivo aparte (``sal.bin``), fuera del repositorio.
"""
import hashlib
import hmac
import os
import re
from pathlib import Path

from .excepciones import AlmacenamientoError, DatoInvalidoError

LONGITUD_DNI = 8
LONGITUD_SAL = 16
ITERACIONES_POR_DEFECTO = 100_000


def validar_dni(dni: str) -> str:
    """Devuelve el DNI sin espacios o lanza DatoInvalidoError si no tiene 8 dígitos."""
    if not isinstance(dni, str):
        raise DatoInvalidoError("El DNI debe ingresarse como texto.")
    dni = dni.strip()
    # ``str.isdigit()`` acepta dígitos Unicode (por ejemplo, de ancho completo
    # o superíndices); la expresión regular exige exactamente dígitos ASCII.
    if not re.fullmatch(rf"[0-9]{{{LONGITUD_DNI}}}", dni):
        raise DatoInvalidoError(f"El DNI debe tener {LONGITUD_DNI} dígitos numéricos.")
    return dni


class GestorSeguridad:
    """Calcula y compara hashes de DNI usando una sal persistente."""

    def __init__(self, ruta_sal, iteraciones: int = ITERACIONES_POR_DEFECTO):
        self._ruta_sal = Path(ruta_sal)
        self._iteraciones = iteraciones
        self.__sal = self._cargar_o_crear_sal()

    def _cargar_o_crear_sal(self) -> bytes:
        """Lee la sal del archivo; si no existe, la crea una única vez."""
        try:
            if self._ruta_sal.exists():
                sal = self._ruta_sal.read_bytes()
                if len(sal) != LONGITUD_SAL:
                    raise AlmacenamientoError("El archivo de sal está dañado.")
                return sal
            self._ruta_sal.parent.mkdir(parents=True, exist_ok=True)
            sal = os.urandom(LONGITUD_SAL)
            self._ruta_sal.write_bytes(sal)
            return sal
        except OSError as error:
            raise AlmacenamientoError(f"No se pudo acceder a la sal: {error}") from error

    def proteger_dni(self, dni: str) -> str:
        """Devuelve el hash hexadecimal del DNI (nunca el DNI)."""
        dni = validar_dni(dni)
        derivado = hashlib.pbkdf2_hmac(
            "sha256", dni.encode("utf-8"), self.__sal, self._iteraciones
        )
        return derivado.hex()

    def coincide(self, dni: str, hash_guardado: str) -> bool:
        """Compara un DNI con un hash guardado en tiempo constante."""
        return hmac.compare_digest(self.proteger_dni(dni), hash_guardado)
