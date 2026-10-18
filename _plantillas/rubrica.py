# -*- coding: utf-8 -*-
"""La rúbrica de una tarea: leerla de TAREA.md, importarla del .docx del
docente y volver a escribirla.

En TAREA.md la rúbrica es una tabla con estas columnas:

    | ID | Criterio | Puntaje | Dónde se cumple |

El ID (C1, C2...) es lo que conecta cada criterio con el documento: en
generar_documento.py, `titulo(doc, "...", 1, criterios="C1")` marca la sección
que lo cubre, y `tareas.py comprobar` lo verifica en el .docx generado. Las
tablas antiguas sin columna ID siguen funcionando: los IDs se asignan por
orden.
"""
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import ficha

ENCABEZADO = ("ID", "Criterio", "Puntaje", "Dónde se cumple")

# Criterios que no corresponden a una sección sino a todo el documento.
_TRANSVERSAL = re.compile(
    r"ortograf|redacci|gram[aá]tic|formato|presentaci|normas apa|\bapa\b|puntualidad|"
    r"entrega a tiempo|coherencia|cohesi[oó]n|estilo|limpieza",
    re.I,
)
_REFERENCIAS = re.compile(r"referencia|bibliograf|\bcita|fuentes", re.I)


@dataclass
class Criterio:
    id: str
    texto: str
    puntaje: float | None = None
    donde: str = ""

    @property
    def de_referencias(self) -> bool:
        return bool(_REFERENCIAS.search(self.texto))

    @property
    def transversal(self) -> bool:
        return bool(_TRANSVERSAL.search(self.texto)) and not self.de_referencias


def normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sin_tildes.lower().strip()


def numero(texto: str | None) -> float | None:
    """'2,5 pts' → 2.5; '20 %' → 20.0; '' → None."""
    if not texto:
        return None
    m = re.search(r"\d+(?:[.,]\d+)?", texto)
    return float(m[0].replace(",", ".")) if m else None


def formatear_puntaje(valor: float | None) -> str:
    if valor is None:
        return ""
    return str(int(valor)) if valor == int(valor) else f"{valor:g}".replace(".", ",")


def _columnas(encabezados: list[str]) -> dict:
    """Identifica qué columna es cada cosa a partir de los encabezados."""
    cols = {}
    for i, enc in enumerate(encabezados):
        e = normalizar(enc)
        if "id" not in cols and e in ("id", "#", "no", "no.", "n", "nº", "n°", "num", "item"):
            cols["id"] = i
        elif "donde" not in cols and e.startswith("donde"):
            cols["donde"] = i
        elif "puntaje" not in cols and re.search(r"puntaje|puntos|pts|peso|valor|ponderaci|%|nota|calificaci", e):
            cols["puntaje"] = i
        elif "criterio" not in cols and re.search(r"criterio|descripci|indicador|aspecto|elemento|dimensi", e):
            cols["criterio"] = i
    return cols


def _desde_filas(encabezados: list[str], filas: list[list[str]]) -> list[Criterio]:
    cols = _columnas(encabezados)
    if "criterio" not in cols:
        return []
    criterios = []
    for fila in filas:
        def celda(clave):
            i = cols.get(clave)
            return ficha.sin_comentarios(fila[i]) if i is not None and i < len(fila) else ""
        texto = celda("criterio")
        if not texto or normalizar(texto) in ("total", "puntaje total", "nota final"):
            continue
        ident = celda("id").upper() or f"C{len(criterios) + 1}"
        if not re.fullmatch(r"[A-Z0-9]+", ident):
            ident = f"C{len(criterios) + 1}"
        criterios.append(Criterio(ident, texto, numero(celda("puntaje")), celda("donde")))
    return criterios


# --------------------------------------------------------------------------
# TAREA.md
# --------------------------------------------------------------------------
def _tabla_rubrica(texto: str):
    lineas = texto.splitlines()
    rango = ficha.seccion(texto, "Rúbrica")
    if rango is None:
        return lineas, None
    for t in ficha.tablas(lineas, *rango):
        if "criterio" in _columnas(t[2]):
            return lineas, t
    return lineas, None


def leer(ruta_tarea: Path) -> list[Criterio]:
    """Criterios de la tabla de la sección '## Rúbrica' de TAREA.md."""
    texto = Path(ruta_tarea).read_text(encoding="utf-8")
    _, t = _tabla_rubrica(texto)
    return _desde_filas(t[2], t[3]) if t else []


def como_tabla(criterios: list[Criterio]) -> list[str]:
    lineas = ["| " + " | ".join(ENCABEZADO) + " |", "|---|---|---|---|"]
    for c in criterios:
        celdas = (c.id, c.texto, formatear_puntaje(c.puntaje), c.donde)
        lineas.append("| " + " | ".join(ficha.escapar_celda(x) for x in celdas) + " |")
    return lineas


def escribir(ruta_tarea: Path, criterios: list[Criterio]) -> None:
    """Sustituye la tabla de la rúbrica de TAREA.md (o la añade si no hay)."""
    ruta_tarea = Path(ruta_tarea)
    texto = ruta_tarea.read_text(encoding="utf-8")
    lineas, t = _tabla_rubrica(texto)
    nueva = como_tabla(criterios)
    if t:
        lineas[t[0]:t[1]] = nueva
    else:
        rango = ficha.seccion(texto, "Rúbrica")
        if rango is None:
            lineas += ["", "## Rúbrica", ""] + nueva
        else:
            fin = rango[1]
            while fin > rango[0] and not lineas[fin - 1].strip():
                fin -= 1
            lineas[fin:fin] = [""] + nueva
    ruta_tarea.write_text("\n".join(lineas) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------
# Importar del documento del docente
# --------------------------------------------------------------------------
def _maximo(textos) -> float | None:
    valores = [numero(t) for t in textos]
    valores = [v for v in valores if v is not None]
    return max(valores) if valores else None


def importar_docx(ruta: Path) -> list[Criterio]:
    """Busca la tabla de rúbrica en un .docx del docente.

    Reconoce dos formas habituales:
      - tabla simple: columnas Criterio | Puntaje (| ...);
      - matriz de niveles: Criterio | Excelente (4) | Bueno (3) | ...; el
        puntaje del criterio es el valor más alto de su fila o, si las celdas
        no traen números, el más alto de los encabezados.
    """
    from docx import Document

    doc = Document(str(ruta))
    for tabla in doc.tables:
        filas = [[c.text.strip() for c in fila.cells] for fila in tabla.rows]
        if len(filas) < 2:
            continue
        encabezados = filas[0]
        cols = _columnas(encabezados)
        if "criterio" not in cols:
            # Tabla de niveles sin encabezado reconocible: primera columna = criterio.
            if _maximo(encabezados[1:]) is None:
                continue
            cols = {"criterio": 0}
        criterios = []
        for fila in filas[1:]:
            texto = fila[cols["criterio"]].split("\n")[0].strip()
            if not texto or normalizar(texto) in ("total", "puntaje total", "nota final"):
                continue
            if "puntaje" in cols:
                puntaje = numero(fila[cols["puntaje"]])
            else:
                otras = [c for i, c in enumerate(fila) if i != cols["criterio"]]
                puntaje = _maximo(otras) or _maximo(encabezados[1:])
            criterios.append(Criterio(f"C{len(criterios) + 1}", texto, puntaje))
        if criterios:
            return criterios
    return []
