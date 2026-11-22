# -*- coding: utf-8 -*-
"""Lee los datos personales del archivo .env de la raíz del repositorio.

El .env es obligatorio para crear tareas y generar documentos, porque la
portada y los nombres de archivo dependen de estos datos. Se crea copiando
.env.example y rellenándolo.

Además admite preferencias opcionales de extensión y profundidad (ver
preferencias()): sin ellas el kit se comporta como siempre.

La variable de entorno RUBRIC_DRIVEN_ENV permite apuntar a otro archivo (la
usan los tests para no tocar el .env real).
"""
import os
import sys
import unicodedata
from dataclasses import dataclass
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
    preferencias(valores)  # valida las opcionales para avisar pronto
    return valores


def cargar_o_salir() -> dict:
    try:
        return cargar()
    except ConfigError as e:
        sys.exit(f"Error de configuración: {e}")


# --------------------------------------------------------------------------
# Preferencias de extensión y profundidad (opcionales)
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Perfil:
    """Cuánto se elabora un documento."""
    nombre: str
    referencias_min: int
    palabras: int  # extensión orientativa si nada más la fija
    guia: str


PROFUNDIDADES = {
    "basica": Perfil("básica", 3, 1200,
                     "fundamentos breves, explicación directa y aplicada al caso"),
    "media": Perfil("media", 4, 1500,
                    "una sección de fundamentos y cada decisión justificada"),
    "alta": Perfil("alta", 8, 2200,
                   "contraste de fuentes, alternativas discutidas y limitaciones"),
}


@dataclass(frozen=True)
class Preferencias:
    """Valores opcionales del .env. None = sin preferencia (comportamiento clásico)."""
    nivel: str | None = None
    profundidad: str | None = None
    paginas_tarea: int | None = None
    paginas_proyecto: int | None = None


def clave_profundidad(texto: str | None) -> str | None:
    """'Básica' → 'basica'; vacío → None; desconocida → ConfigError."""
    if not texto or not texto.strip():
        return None
    clave = unicodedata.normalize("NFKD", texto.strip().lower()).encode("ascii", "ignore").decode()
    if clave not in PROFUNDIDADES:
        raise ConfigError(f"profundidad desconocida «{texto}»; usa básica, media o alta.")
    return clave


def _entero_positivo(valores: dict, clave: str) -> int | None:
    texto = (valores.get(clave) or "").strip()
    if not texto:
        return None
    if not texto.isdigit() or int(texto) == 0:
        raise ConfigError(f"{clave} debe ser un número entero de páginas mayor que 0 (hay «{texto}»).")
    return int(texto)


def preferencias(valores: dict | None = None) -> Preferencias:
    """Lee NIVEL_ACADEMICO, PROFUNDIDAD, PAGINAS_MAX_TAREA y PAGINAS_MAX_PROYECTO.

    Todas son opcionales y no exigen el resto del .env: sin .env se devuelven
    preferencias vacías. Un valor mal escrito lanza ConfigError.
    """
    if valores is None:
        valores = _leer_env(ARCHIVO_ENV) if ARCHIVO_ENV.exists() else {}
    return Preferencias(
        nivel=(valores.get("NIVEL_ACADEMICO") or "").strip() or None,
        profundidad=clave_profundidad(valores.get("PROFUNDIDAD")),
        paginas_tarea=_entero_positivo(valores, "PAGINAS_MAX_TAREA"),
        paginas_proyecto=_entero_positivo(valores, "PAGINAS_MAX_PROYECTO"),
    )
