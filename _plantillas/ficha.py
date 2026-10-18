# -*- coding: utf-8 -*-
"""Lectura y escritura de las fichas en Markdown: TAREA.md y el README.md de
cada materia.

Las fichas son texto libre para personas, así que el análisis es tolerante:
los comentarios HTML (<!-- ... -->) cuentan como campos vacíos y los campos
que no aparecen se devuelven como None.
"""
import datetime
import re
from dataclasses import dataclass, field
from pathlib import Path

PALABRAS_POR_PAGINA = 275  # Times New Roman 12 a doble espacio, aproximado

_COMENTARIO = re.compile(r"<!--.*?-->", re.S)
_CAMPO = re.compile(r"^\s*-\s*\*\*(?P<campo>[^*]+?):\*\*\s*(?P<valor>.*)$")


def sin_comentarios(texto: str) -> str:
    return _COMENTARIO.sub("", texto).strip()


# --------------------------------------------------------------------------
# Markdown mínimo: secciones, campos y tablas
# --------------------------------------------------------------------------
def seccion(texto: str, nombre: str) -> tuple[int, int] | None:
    """Rango [inicio, fin) de las líneas bajo '## <nombre>' (sin el título)."""
    lineas = texto.splitlines()
    inicio = None
    for i, linea in enumerate(lineas):
        if re.match(r"^##\s+", linea):
            if inicio is not None:
                return inicio, i
            if linea[2:].strip().lower() == nombre.lower():
                inicio = i + 1
    return (inicio, len(lineas)) if inicio is not None else None


def campos(texto: str) -> dict:
    """Campos '- **Clave:** valor' → {'clave': 'valor'} (claves en minúsculas)."""
    valores = {}
    for linea in texto.splitlines():
        m = _CAMPO.match(linea)
        if m:
            valores[m["campo"].strip().lower()] = sin_comentarios(m["valor"])
    return valores


def reemplazar_campo(texto: str, campo: str, valor: str) -> str:
    patron = re.compile(r"^(\s*-\s*\*\*" + re.escape(campo) + r":\*\*\s*).*$", re.M | re.I)
    if not patron.search(texto):
        raise KeyError(f"no hay un campo '{campo}'")
    return patron.sub(lambda m: m[1] + valor, texto, count=1)


def celdas(linea: str) -> list[str]:
    """'| a | b \\| c |' → ['a', 'b | c']."""
    interior = linea.strip()
    interior = interior[1:] if interior.startswith("|") else interior
    interior = interior[:-1] if interior.endswith("|") and not interior.endswith("\\|") else interior
    partes = re.split(r"(?<!\\)\|", interior)
    return [p.strip().replace("\\|", "|") for p in partes]


def es_separador(linea: str) -> bool:
    return bool(re.fullmatch(r"\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*", linea))


def tablas(lineas: list[str], desde: int = 0, hasta: int | None = None):
    """Devuelve las tablas como (inicio, fin, encabezados, filas)."""
    hasta = len(lineas) if hasta is None else hasta
    i = desde
    while i < hasta:
        if lineas[i].lstrip().startswith("|") and i + 1 < hasta and es_separador(lineas[i + 1]):
            inicio = i
            encabezados = celdas(lineas[i])
            filas = []
            i += 2
            while i < hasta and lineas[i].lstrip().startswith("|"):
                filas.append(celdas(lineas[i]))
                i += 1
            yield inicio, i, encabezados, filas
        else:
            i += 1


def escapar_celda(texto) -> str:
    return str(texto).replace("|", "\\|").replace("\n", " ")


# --------------------------------------------------------------------------
# Valores de los campos
# --------------------------------------------------------------------------
def leer_fecha(texto: str | None) -> datetime.date | None:
    """Acepta AAAA-MM-DD y DD/MM/AAAA."""
    if not texto:
        return None
    m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", texto)
    if m:
        a, mes, d = map(int, m.groups())
    else:
        m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", texto)
        if not m:
            return None
        d, mes, a = map(int, m.groups())
    try:
        return datetime.date(a, mes, d)
    except ValueError:
        return None


def leer_extension(texto: str | None) -> int | None:
    """'1500 palabras' → 1500; '4-6 páginas' → 5 × PALABRAS_POR_PAGINA."""
    if not texto:
        return None
    numeros = [int(n) for n in re.findall(r"\d+", texto.replace(".", ""))]
    if not numeros:
        return None
    media = sum(numeros) / len(numeros)
    if re.search(r"p[áa]g", texto, re.I):
        media *= PALABRAS_POR_PAGINA
    return int(round(media))


# --------------------------------------------------------------------------
# Fichas
# --------------------------------------------------------------------------
@dataclass
class Materia:
    carpeta: Path
    nombre: str
    docente: str | None = None
    formato: str | None = None


@dataclass
class Tarea:
    carpeta: Path
    codigo: str
    titulo: str
    materia: Materia
    estado: str = "pendiente"
    fecha: datetime.date | None = None
    extension: int | None = None
    formato: str | None = None
    campos: dict = field(default_factory=dict)

    @property
    def ruta(self) -> Path:
        return self.carpeta / "TAREA.md"

    @property
    def base(self) -> str:
        return self.carpeta.name


def leer_materia(carpeta: Path) -> Materia:
    carpeta = Path(carpeta)
    readme = carpeta / "README.md"
    if not readme.exists():
        return Materia(carpeta, carpeta.name)
    texto = readme.read_text(encoding="utf-8")
    nombre = next((l[2:].strip() for l in texto.splitlines() if l.startswith("# ")), carpeta.name)
    datos = {}
    for _, _, _, filas in tablas(texto.splitlines()):
        for fila in filas:
            if len(fila) >= 2:
                datos[fila[0].strip("* ").lower()] = sin_comentarios(fila[1]) or None
    return Materia(carpeta, nombre, datos.get("docente"), datos.get("formato que pide el docente"))


def leer_tarea(carpeta: Path) -> Tarea:
    carpeta = Path(carpeta).resolve()
    ruta = carpeta / "TAREA.md"
    if not ruta.exists():
        raise FileNotFoundError(f"No existe {ruta}")
    texto = ruta.read_text(encoding="utf-8")
    primera = next((l[2:].strip() for l in texto.splitlines() if l.startswith("# ")), carpeta.name)
    codigo, _, titulo = primera.partition(" — ")
    datos = campos(texto)
    rango = seccion(texto, "Formato")
    formato = sin_comentarios("\n".join(texto.splitlines()[slice(*rango)])) if rango else None
    return Tarea(
        carpeta=carpeta,
        codigo=codigo.strip() or carpeta.name.split("_")[0],
        titulo=titulo.strip() or primera,
        materia=leer_materia(carpeta.parent),
        estado=(datos.get("estado") or "pendiente").lower(),
        fecha=leer_fecha(datos.get("fecha de entrega")),
        extension=leer_extension(datos.get("extensión") or datos.get("extension")),
        formato=formato or None,
        campos=datos,
    )


def marcar_estado(tarea: Tarea, estado: str) -> list[Path]:
    """Cambia 'Estado:' en TAREA.md y la fila de la tabla del README de la materia."""
    cambiados = []
    texto = tarea.ruta.read_text(encoding="utf-8")
    tarea.ruta.write_text(reemplazar_campo(texto, "Estado", estado), encoding="utf-8")
    cambiados.append(tarea.ruta)

    readme = tarea.materia.carpeta / "README.md"
    if readme.exists():
        lineas = readme.read_text(encoding="utf-8").splitlines()
        for i, linea in enumerate(lineas):
            fila = celdas(linea) if linea.lstrip().startswith("|") else []
            if len(fila) >= 3 and fila[0].strip("`") == tarea.base:
                fila[-1] = estado
                lineas[i] = "| " + " | ".join(escapar_celda(c) for c in fila) + " |"
                readme.write_text("\n".join(lineas) + "\n", encoding="utf-8")
                cambiados.append(readme)
                break
    return cambiados
