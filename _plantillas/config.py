# -*- coding: utf-8 -*-
"""Lee los datos personales del archivo .env de la raíz del repositorio.

El .env es obligatorio para crear tareas y generar documentos, porque la
portada y los nombres de archivo dependen de estos datos. Se crea copiando
.env.example y rellenándolo.

La variable de entorno RUBRIC_DRIVEN_ENV permite apuntar a otro archivo (la
usan los tests para no tocar el .env real).
"""
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARCHIVO_ENV = Path(os.environ.get("RUBRIC_DRIVEN_ENV") or RAIZ / ".env")

OBLIGATORIAS = {
    "NOMBRE_ESTUDIANTE": "nombre completo que va en la portada",
    "INSTITUCION": "institución que va en la portada",
    "CARRERA": "carrera que va en la portada",
    "SUFIJO_ARCHIVOS": "sufijo de los entregables, p. ej. Perez_Ana",
}


class ConfigError(Exception):
    pass


def _leer_env(ruta: Path) -> dict:
    valores = {}
    for n, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        if "=" not in linea:
            raise ConfigError(f"{ruta.name}, línea {n}: falta '=' en «{linea}»")
        clave, valor = linea.split("=", 1)
        valor = valor.strip()
        if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
            valor = valor[1:-1]
        valores[clave.strip()] = valor
    return valores


def cargar() -> dict:
    """Devuelve la configuración o lanza ConfigError explicando qué falta."""
    if not ARCHIVO_ENV.exists():
        raise ConfigError(
            "No existe el archivo .env en la raíz del repositorio.\n"
            "  Créalo con:  cp .env.example .env   y rellena tus datos."
        )
    valores = _leer_env(ARCHIVO_ENV)
    faltan = [f"  - {k}: {desc}" for k, desc in OBLIGATORIAS.items() if not valores.get(k)]
    if faltan:
        raise ConfigError("Faltan datos en .env:\n" + "\n".join(faltan))
    return valores


def cargar_o_salir() -> dict:
    try:
        return cargar()
    except ConfigError as e:
        sys.exit(f"Error de configuración: {e}")
