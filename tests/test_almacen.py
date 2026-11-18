from datetime import date, timedelta
import json

import pytest

from sistemarural.almacen import AlmacenJSON
from sistemarural.excepciones import AlmacenamientoError


def test_cargar_archivo_inexistente_devuelve_diccionario_vacio(tmp_path):
    assert AlmacenJSON(tmp_path / "centro.json").cargar() == {}


def test_guardar_y_cargar_json_con_unicode(tmp_path):
    almacen = AlmacenJSON(tmp_path / "datos" / "centro.json")
    datos = {"nombre": "José", "citas": [1, 2]}

    almacen.guardar(datos)

    assert almacen.cargar() == datos


def test_cargar_json_danado_lanza_error(tmp_path):
    ruta = tmp_path / "roto.json"
    ruta.write_text("{no es json", encoding="utf-8")

    with pytest.raises(AlmacenamientoError, match="dañado"):
        AlmacenJSON(ruta).cargar()


def test_cargar_json_que_no_es_diccionario_lanza_error(tmp_path):
    ruta = tmp_path / "lista.json"
    ruta.write_text(json.dumps([1, 2]), encoding="utf-8")

    with pytest.raises(AlmacenamientoError, match="formato esperado"):
        AlmacenJSON(ruta).cargar()


def test_guardar_dato_no_serializable_lanza_error_y_no_deja_temporal(tmp_path):
    almacen = AlmacenJSON(tmp_path / "centro.json")

    with pytest.raises(AlmacenamientoError, match="guardar"):
        almacen.guardar({"fecha": date.today()})

    assert not list(tmp_path.glob("*.tmp"))
