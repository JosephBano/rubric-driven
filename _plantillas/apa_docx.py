# -*- coding: utf-8 -*-
"""
Plantilla reutilizable para generar informes .docx en normas APA 7 (trabajo
de estudiante). El texto es monocromático; las figuras conservan su color
original, porque en una captura el color suele ser información.

Los datos del estudiante (portada y sufijo de archivos) se leen del .env de
la raíz del repositorio la primera vez que se necesitan, no al importar.

Uso típico en el script de una actividad (lo genera `tareas.py tarea`):

    import sys
    from pathlib import Path
    AQUI = Path(__file__).resolve().parent
    sys.path.insert(0, str(AQUI.parents[2] / "_plantillas"))  # materias/<materia>/<tarea>/
    from apa_docx import *

    SALIDA = AQUI / nombre_entregable("A15_Titulo_Corto")   # + sufijo del .env
    bib = Bibliografia()
    bib.agregar("oracle2024", ["Oracle"], 2024, "MySQL 8.4 reference manual",
                url="https://dev.mysql.com/doc/refman/8.4/en/")

    doc, figura, tabla = nuevo_documento(
        titulo="Título del Informe",
        materia="Nombre de la Materia",
        salida=SALIDA,
        tarea=AQUI,           # docente y fecha de entrega desde TAREA.md
    )

    parrafo(doc, "Introducción, sin encabezado como pide APA 7...")
    titulo(doc, "Procedimientos almacenados", 1, criterios="C1")
    parrafo(doc, f"Texto con cita {bib.cita('oracle2024')}.")
    figura(doc, None, "Descripción de la figura", "fig1.png", "Nota explicativa.")
    tabla(doc, None, "Descripción de la tabla", ["Col A", "Col B"], [("x", "y")])
    transversal(doc, "C5")    # p. ej. "Ortografía y redacción"
    referencias(doc, bib)

    guardar_documento(doc, SALIDA)

Ver también PLANTILLA_README.md en esta misma carpeta.
"""
import datetime
import itertools
import os
import re
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

import config

__all__ = [
    "Bibliografia", "NEGRO", "WD_ALIGN_PARAGRAPH",
    "NOMBRE_ESTUDIANTE", "INSTITUCION", "CARRERA", "SUFIJO_ARCHIVOS",
    "codigo", "convertir_a_grises", "fecha_hoy", "fecha_portada", "guardar_documento",
    "leer_fuente", "nombre_entregable", "nuevo_documento", "parrafo", "referencia",
    "referencias", "salto_de_pagina", "tabla", "titulo", "transversal", "vinieta",
]

NEGRO = RGBColor(0, 0, 0)
FUENTE = "Times New Roman"
IDIOMA = "es-ES"
PREFIJO_MARCA = "rubrica_"
SUFIJO_TRANSVERSAL = "_todo"

_MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
          "agosto", "septiembre", "octubre", "noviembre", "diciembre")

# --------------------------------------------------------------------------
# Datos del estudiante: se leen del .env al primer uso
# --------------------------------------------------------------------------
_CONSTANTES_ENV = ("NOMBRE_ESTUDIANTE", "INSTITUCION", "CARRERA", "SUFIJO_ARCHIVOS")
_config = None


def _cfg() -> dict:
    global _config
    if _config is None:
        _config = config.cargar_o_salir()
    return _config


def __getattr__(nombre):
    # NOMBRE_ESTUDIANTE, INSTITUCION... siguen disponibles como antes, pero
    # solo leen el .env cuando alguien los usa.
    if nombre in _CONSTANTES_ENV:
        return _cfg()[nombre]
    raise AttributeError(f"module {__name__!r} has no attribute {nombre!r}")


def fecha_portada(fecha: datetime.date | None = None) -> str:
    """date(2026, 9, 23) → '23 de septiembre de 2026' (hoy si no se indica)."""
    fecha = fecha or datetime.date.today()
    return f"{fecha.day} de {_MESES[fecha.month - 1]} de {fecha.year}"


def fecha_hoy() -> str:
    return fecha_portada()


def nombre_entregable(base, extension=".docx"):
    """'A15_Titulo' -> 'A15_Titulo_<SUFIJO_ARCHIVOS>.docx'."""
    return f"{base}_{_cfg()['SUFIJO_ARCHIVOS']}{extension}"


# --------------------------------------------------------------------------
# Utilidades de bajo nivel
# --------------------------------------------------------------------------
def _fuente_fija(rpr, nombre=FUENTE):
    """Fija la fuente en todos los alfabetos y quita las fuentes de tema
    (los estilos de encabezado de Word traen Calibri Light por tema, que
    tiene prioridad sobre el nombre de fuente)."""
    for viejo in rpr.findall(qn("w:rFonts")):
        rpr.remove(viejo)
    fuentes = OxmlElement("w:rFonts")
    for atributo in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        fuentes.set(qn(atributo), nombre)
    rpr.insert(0, fuentes)


def _idioma(rpr, idioma=IDIOMA):
    for viejo in rpr.findall(qn("w:lang")):
        rpr.remove(viejo)
    lang = OxmlElement("w:lang")
    for atributo in ("w:val", "w:eastAsia", "w:bidi"):
        lang.set(qn(atributo), idioma)
    rpr.append(lang)


def _estilos(doc):
    """Normal, encabezados APA 1-3 y viñetas: Times New Roman 12, negro,
    doble espacio. Los encabezados usan los estilos 'Heading N' de Word, así
    que aparecen en el panel de navegación, en el índice y como marcadores
    del PDF."""
    normal = doc.styles["Normal"]
    normal.font.name = FUENTE
    normal.font.size = Pt(12)
    normal.font.color.rgb = NEGRO
    _fuente_fija(normal.element.get_or_add_rPr())
    _idioma(normal.element.get_or_add_rPr())
    normal.paragraph_format.line_spacing = 2.0
    normal.paragraph_format.space_after = Pt(0)

    for nivel in (1, 2, 3):
        est = doc.styles[f"Heading {nivel}"]
        est.font.size = Pt(12)
        est.font.bold = True
        est.font.italic = nivel == 3
        est.font.color.rgb = NEGRO
        _fuente_fija(est.element.get_or_add_rPr())
        pf = est.paragraph_format
        pf.alignment = WD_ALIGN_PARAGRAPH.CENTER if nivel == 1 else WD_ALIGN_PARAGRAPH.LEFT
        pf.line_spacing = 2.0
        pf.space_before = Pt(12 if nivel == 1 else 10)
        pf.space_after = Pt(0)
        pf.keep_with_next = True
        pf.first_line_indent = Inches(0)

    viñetas = doc.styles["List Bullet"]
    viñetas.font.color.rgb = NEGRO


def _numero_de_pagina(section):
    p = section.header.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p.paragraph_format.line_spacing = 1.0
    _campo(p, "PAGE")


def _campo(parrafo_, instruccion, texto_previo=""):
    run = parrafo_.add_run()
    inicio = OxmlElement("w:fldChar")
    inicio.set(qn("w:fldCharType"), "begin")
    inicio.set(qn("w:dirty"), "true")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = f" {instruccion} "
    separa = OxmlElement("w:fldChar")
    separa.set(qn("w:fldCharType"), "separate")
    fin = OxmlElement("w:fldChar")
    fin.set(qn("w:fldCharType"), "end")
    run._r.append(inicio)
    run._r.append(instr)
    run._r.append(separa)
    if texto_previo:
        t = OxmlElement("w:t")
        t.text = texto_previo
        run._r.append(t)
    run._r.append(fin)
    run.font.color.rgb = NEGRO
    return run


_ids_marca = itertools.count(1)


def _marcar(parrafo_, nombre):
    """Marcador invisible: así el .docx recuerda qué criterio cubre cada sección."""
    ident = str(next(_ids_marca))
    inicio = OxmlElement("w:bookmarkStart")
    inicio.set(qn("w:id"), ident)
    inicio.set(qn("w:name"), nombre[:40])
    fin = OxmlElement("w:bookmarkEnd")
    fin.set(qn("w:id"), ident)
    parrafo_._p.insert(1 if parrafo_._p.pPr is not None else 0, inicio)
    parrafo_._p.append(fin)


def _ids_criterios(criterios) -> list[str]:
    if criterios is None:
        return []
    if isinstance(criterios, str):
        criterios = re.split(r"[,\s]+", criterios)
    ids = [c.strip().upper() for c in criterios if c and c.strip()]
    for c in ids:
        if not re.fullmatch(r"[A-Z0-9]+", c):
            raise ValueError(f"ID de criterio no válido: {c!r} (usa C1, C2...)")
    return ids


def _set_borde_celda(celda, color="000000", tam="4"):
    tc_pr = celda._tc.get_or_add_tcPr()
    bordes = OxmlElement("w:tcBorders")
    for lado in ("top", "left", "bottom", "right"):
        el = OxmlElement("w:%s" % lado)
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), tam)
        el.set(qn("w:color"), color)
        bordes.append(el)
    tc_pr.append(bordes)


def _sombrear_celda(celda, hexcolor="D9D9D9"):
    tc_pr = celda._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hexcolor)
    tc_pr.append(shd)


def _texto_con_cursivas(p, texto, tamano=12):
    """Añade `texto` a `p`; lo que va entre *asteriscos* sale en cursiva."""
    for i, trozo in enumerate(re.split(r"\*([^*]+)\*", texto)):
        if not trozo:
            continue
        r = p.add_run(trozo)
        r.italic = i % 2 == 1
        r.font.size = Pt(tamano)
        r.font.color.rgb = NEGRO


def _siguiente(doc, clave):
    estado = doc.__dict__.setdefault("_rubric_driven", {})
    estado[clave] = estado.get(clave, 0) + 1
    return estado[clave]


# --------------------------------------------------------------------------
# Bloques de contenido
# --------------------------------------------------------------------------
def parrafo(doc, texto="", *, alineacion=WD_ALIGN_PARAGRAPH.JUSTIFY,
            sangria=True, espaciado=2.0, negrita=False, cursiva=False,
            tamano=12, antes=0, despues=0):
    p = doc.add_paragraph()
    p.alignment = alineacion
    pf = p.paragraph_format
    pf.line_spacing = espaciado
    pf.space_before = Pt(antes)
    pf.space_after = Pt(despues)
    if sangria:
        pf.first_line_indent = Inches(0.5)
    if texto:
        r = p.add_run(texto)
        r.bold = negrita
        r.italic = cursiva
        r.font.size = Pt(tamano)
        r.font.color.rgb = NEGRO
    return p


def titulo(doc, texto, nivel=1, criterios=None):
    """Encabezado APA 7 con estilo de Word 'Heading N'.

    nivel 1: centrado y negrita (secciones principales).
    nivel 2: alineado a la izquierda, negrita.
    nivel 3: alineado a la izquierda, negrita y cursiva.

    criterios: IDs de la rúbrica que cubre esta sección ("C1" o ["C1", "C2"]).
    Se guardan como marcadores invisibles en el .docx y los usa
    `tareas.py comprobar` para verificar la cobertura.
    """
    nivel = min(max(int(nivel), 1), 3)
    p = doc.add_paragraph(texto, style=f"Heading {nivel}")
    for ident in _ids_criterios(criterios):
        _marcar(p, PREFIJO_MARCA + ident)
    return p


def transversal(doc, *criterios):
    """Declara criterios que se cumplen en todo el documento (ortografía,
    formato APA...). No tienen sección propia ni cuentan para el reparto de
    extensión."""
    ids = _ids_criterios(list(criterios) if len(criterios) != 1 else criterios[0])
    p = doc.paragraphs[-1]
    for ident in ids:
        _marcar(p, PREFIJO_MARCA + ident + SUFIJO_TRANSVERSAL)


def vinieta(doc, texto):
    p = doc.add_paragraph(style="List Bullet")
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf = p.paragraph_format
    pf.line_spacing = 2.0
    pf.space_after = Pt(0)
    pf.left_indent = Inches(0.5)
    r = p.add_run(texto)
    r.font.size = Pt(12)
    r.font.color.rgb = NEGRO
    return p


def codigo(doc, texto, tamano=8.5):
    """Bloque de código/comandos monoespaciado a espacio sencillo."""
    for linea in texto.split("\n"):
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.line_spacing = 1.0
        pf.space_before = Pt(0)
        pf.space_after = Pt(0)
        pf.left_indent = Inches(0.4)
        pf.first_line_indent = Inches(0)
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r = p.add_run(linea if linea.strip() else " ")
        r.font.name = "Courier New"
        _fuente_fija(r._element.get_or_add_rPr(), "Courier New")
        r.font.size = Pt(tamano)
        r.font.color.rgb = NEGRO


def salto_de_pagina(doc):
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def referencia(doc, texto):
    """Entrada de la lista de referencias con sangría francesa.
    Lo que va entre *asteriscos* sale en cursiva (títulos de libros, revistas)."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pf = p.paragraph_format
    pf.line_spacing = 2.0
    pf.left_indent = Inches(0.5)
    pf.first_line_indent = Inches(-0.5)
    pf.space_after = Pt(0)
    _texto_con_cursivas(p, texto)
    return p


def _make_figura(carpeta_capturas):
    """Genera la función figura() con la carpeta de capturas ya fijada."""
    def figura(doc, numero, descripcion, archivo, nota, ancho=5.5):
        """numero=None numera automáticamente (Figura 1, 2...)."""
        numero = _siguiente(doc, "figura") if numero is None else numero
        p = doc.add_paragraph()
        p.paragraph_format.line_spacing = 2.0
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.keep_with_next = True
        r = p.add_run("Figura %s" % numero)
        r.bold = True
        r.font.size = Pt(12)
        r.font.color.rgb = NEGRO

        p = doc.add_paragraph()
        p.paragraph_format.line_spacing = 2.0
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(descripcion)
        r.italic = True
        r.font.size = Pt(12)
        r.font.color.rgb = NEGRO

        ruta = os.fspath(archivo)
        if not os.path.isabs(ruta):
            ruta = os.path.join(carpeta_capturas, ruta)
        if os.path.exists(ruta):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(6)
            p.paragraph_format.line_spacing = 1.0
            p.paragraph_format.keep_with_next = True
            p.add_run().add_picture(ruta, width=Inches(ancho))
        else:
            parrafo(doc, "[FALTA LA CAPTURA: %s]" % archivo,
                    alineacion=WD_ALIGN_PARAGRAPH.CENTER, sangria=False)

        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.line_spacing = 1.5
        p.paragraph_format.space_after = Pt(12)
        r = p.add_run("Nota. ")
        r.italic = True
        r.font.size = Pt(10)
        r.font.color.rgb = NEGRO
        r2 = p.add_run(nota)
        r2.font.size = Pt(10)
        r2.font.color.rgb = NEGRO
        return numero
    return figura


def tabla(doc, numero, descripcion, encabezados, filas):
    """Tabla en formato APA (Tabla N + descripción en cursiva + tabla con
    bordes finos, encabezado sombreado en gris claro). numero=None numera
    automáticamente. Deja un párrafo después, para que dos tablas seguidas no
    se fusionen (LibreOffice se cuelga con eso)."""
    numero = _siguiente(doc, "tabla") if numero is None else numero
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 2.0
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.keep_with_next = True
    r = p.add_run("Tabla %s" % numero)
    r.bold = True
    r.font.size = Pt(12)
    r.font.color.rgb = NEGRO

    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 2.0
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(descripcion)
    r.italic = True
    r.font.size = Pt(12)
    r.font.color.rgb = NEGRO

    t = doc.add_table(rows=1, cols=len(encabezados))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = True
    # Marca la primera fila como encabezado, para que se repita cuando la
    # tabla se parte entre páginas y las columnas sigan siendo legibles.
    tr_pr = t.rows[0]._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)
    for i, texto in enumerate(encabezados):
        celda = t.rows[0].cells[i]
        _set_borde_celda(celda)
        _sombrear_celda(celda)
        celda.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        celda.paragraphs[0].paragraph_format.line_spacing = 1.0
        r = celda.paragraphs[0].add_run(texto)
        r.bold = True
        r.font.size = Pt(10.5)
        r.font.color.rgb = NEGRO

    for fila in filas:
        if len(fila) != len(encabezados):
            raise ValueError(f"Tabla {numero}: la fila {fila!r} tiene {len(fila)} columnas "
                             f"y el encabezado {len(encabezados)}")
        f = t.add_row()
        # Impide que una fila se parta entre dos páginas dejando una línea
        # suelta arriba; si no cabe entera, salta completa a la siguiente.
        no_partir = OxmlElement("w:cantSplit")
        no_partir.set(qn("w:val"), "true")
        f._tr.get_or_add_trPr().append(no_partir)
        for i, texto in enumerate(fila):
            celda = f.cells[i]
            _set_borde_celda(celda)
            celda.paragraphs[0].alignment = (
                WD_ALIGN_PARAGRAPH.CENTER if i < len(fila) - 1 else WD_ALIGN_PARAGRAPH.LEFT
            )
            celda.paragraphs[0].paragraph_format.line_spacing = 1.0
            r = celda.paragraphs[0].add_run(str(texto))
            r.font.size = Pt(10.5)
            r.font.color.rgb = NEGRO
            if i == 0:
                r.bold = True

    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(10)
    p.paragraph_format.line_spacing = 1.0
    return t


def leer_fuente(ruta):
    with open(ruta, encoding="utf-8") as f:
        return f.read().rstrip()


def convertir_a_grises(carpeta_capturas, patrones=("*.png", "*.jpg", "*.jpeg")):
    """DESACONSEJADA. Convierte a escala de grises las capturas de una carpeta.

    La norma del repositorio es que **las figuras conserven su color
    original**: el texto del documento es monocromático, las imágenes no. En
    una fotografía o una captura el color suele ser información —qué diodo
    está encendido, de qué color es un cable, si una advertencia está en rojo—
    y perderlo empobrece la evidencia sin ganar nada a cambio.

    Esta función se conserva solo para documentos antiguos que ya dependen de
    ella. Reescribe los archivos **en el sitio**, de modo que antes de
    convertir cada imagen guarda una copia intacta en la subcarpeta
    `originales/`, que ningún glob de la plantilla alcanza. Así la conversión
    deja de ser irreversible: basta con volver a copiar desde ahí.
    """
    import glob
    import shutil
    from PIL import Image
    respaldo = os.path.join(carpeta_capturas, "originales")
    os.makedirs(respaldo, exist_ok=True)
    convertidas = []
    for patron in patrones:
        for ruta in glob.glob(os.path.join(carpeta_capturas, patron)):
            copia = os.path.join(respaldo, os.path.basename(ruta))
            if not os.path.exists(copia):
                shutil.copy2(ruta, copia)
            im = Image.open(ruta).convert("L").convert("RGB")
            im.save(ruta, quality=92)
            convertidas.append(ruta)
    return convertidas


# --------------------------------------------------------------------------
# Citas y referencias APA 7
# --------------------------------------------------------------------------
def _apellido(autor: str) -> str:
    """'Ramos, J. A.' → 'Ramos'; 'Oracle' → 'Oracle'."""
    return autor.split(",")[0].strip()


def _unir(elementos, conector="y"):
    if len(elementos) == 1:
        return elementos[0]
    return ", ".join(elementos[:-1]) + f" {conector} " + elementos[-1]


class Bibliografia:
    """Lista de referencias APA 7 con citas en el texto.

        bib = Bibliografia()
        bib.agregar("ramos2024", ["Ramos, J.", "Pérez, A."], 2024,
                    "Bases de datos relacionales", "Alfaomega")
        bib.agregar("oracle2024", ["Oracle"], 2024, "MySQL 8.4 reference manual",
                    url="https://dev.mysql.com/doc/refman/8.4/en/")
        bib.agregar("lee2023", ["Lee, K."], 2023, "Indexing strategies",
                    "Journal of Databases", detalles="12(3), 45–60", tipo="articulo")

        bib.cita("ramos2024")            → '(Ramos y Pérez, 2024)'
        bib.cita("ramos2024", "p. 15")   → '(Ramos y Pérez, 2024, p. 15)'
        bib.cita_narrativa("lee2023")    → 'Lee (2023)'
        referencias(doc, bib)            → sección Referencias en página nueva

    tipo="articulo" o "capitulo" pone en cursiva la fuente (revista, libro);
    el resto pone en cursiva el título. Para casos especiales, `texto=` da la
    entrada completa (con *cursivas* entre asteriscos).
    """

    def __init__(self):
        self._fuentes = {}
        self._citadas = set()

    def agregar(self, clave, autores, anio, titulo="", fuente="", *, url="",
                detalles="", tipo="libro", texto=""):
        if clave in self._fuentes:
            raise ValueError(f"La referencia '{clave}' ya existe")
        if isinstance(autores, str):
            autores = [autores]
        if not autores:
            raise ValueError(f"'{clave}': hace falta al menos un autor (persona u organización)")
        self._fuentes[clave] = dict(autores=list(autores), anio=str(anio), titulo=titulo,
                                    fuente=fuente, url=url, detalles=detalles, tipo=tipo,
                                    texto=texto)
        return clave

    def _fuente(self, clave):
        if clave not in self._fuentes:
            disponibles = ", ".join(sorted(self._fuentes)) or "ninguna"
            raise KeyError(f"No hay referencia '{clave}' (hay: {disponibles})")
        self._citadas.add(clave)
        return self._fuentes[clave]

    def _autores_cita(self, f):
        apellidos = [_apellido(a) for a in f["autores"]]
        if len(apellidos) >= 3:
            return f"{apellidos[0]} et al."
        return " y ".join(apellidos)

    def cita(self, *claves, pagina=""):
        """Cita parentética: '(Ramos, 2024)'; varias claves → '(Lee, 2023; Ramos, 2024)'.
        Una segunda posición textual se toma como página: cita('x', 'p. 15')."""
        if len(claves) == 2 and claves[1] not in self._fuentes and not pagina:
            claves, pagina = claves[:1], claves[1]
        partes = []
        for clave in claves:
            f = self._fuente(clave)
            partes.append(f"{self._autores_cita(f)}, {f['anio']}")
        partes.sort(key=str.lower)
        texto = "; ".join(partes)
        return f"({texto}, {pagina})" if pagina else f"({texto})"

    def cita_narrativa(self, clave, pagina=""):
        """Cita narrativa: 'Ramos y Pérez (2024)'."""
        f = self._fuente(clave)
        sufijo = f", {pagina}" if pagina else ""
        return f"{self._autores_cita(f)} ({f['anio']}{sufijo})"

    def entrada(self, clave) -> str:
        f = self._fuentes[clave]
        if f["texto"]:
            return f["texto"]
        autores = _unir(f["autores"])
        if not autores.endswith("."):
            autores += "."
        partes = [f"{autores} ({f['anio']})."]
        cursiva_fuente = f["tipo"] in ("articulo", "capitulo")
        if f["titulo"]:
            partes.append(f"{f['titulo']}." if cursiva_fuente else f"*{f['titulo']}*.")
        fuente = f["fuente"]
        if fuente and fuente not in f["autores"]:
            fuente = f"*{fuente}*" if cursiva_fuente else fuente
            partes.append(f"{fuente}, {f['detalles']}." if f["detalles"] else f"{fuente}.")
        elif f["detalles"]:
            partes.append(f"{f['detalles']}.")
        if f["url"]:
            partes.append(f["url"])
        return " ".join(partes)

    def no_citadas(self):
        return sorted(set(self._fuentes) - self._citadas)

    def ordenadas(self):
        def orden(clave):
            f = self._fuentes[clave]
            return ([_apellido(a).lower() for a in f["autores"]], f["anio"])
        return sorted(self._citadas, key=orden)


def referencias(doc, bib=None, *, criterios=None, nueva_pagina=True, entradas=()):
    """Sección 'Referencias' (APA 7: página nueva, título centrado en negrita,
    sangría francesa, orden alfabético). Incluye las fuentes de `bib` que se
    hayan citado; `entradas` añade referencias escritas a mano."""
    if nueva_pagina:
        salto_de_pagina(doc)
    titulo(doc, "Referencias", 1, criterios=criterios)
    textos = [bib.entrada(c) for c in bib.ordenadas()] if bib else []
    textos += list(entradas)
    for texto in sorted(textos, key=lambda t: t.lstrip("*").lower()):
        referencia(doc, texto)
    if bib and bib.no_citadas():
        print("Aviso: referencias registradas pero nunca citadas (APA no las admite; "
              "no se incluyen): " + ", ".join(bib.no_citadas()))


# --------------------------------------------------------------------------
# Punto de entrada: crea el documento con portada y estilos ya aplicados
# --------------------------------------------------------------------------
def _desde_tarea(carpeta):
    """Docente y fecha de entrega desde TAREA.md y el README de la materia."""
    import ficha
    try:
        t = ficha.leer_tarea(carpeta)
    except FileNotFoundError:
        return None, None
    return t.materia.docente, t.fecha


def nuevo_documento(*, titulo, materia, salida, fecha=None, docente=None, tarea=None,
                    carpeta_capturas=None, nombre=None, institucion=None, carrera=None,
                    indice=False):
    """Crea el Document(), aplica estilos APA 7, arma la portada de
    estudiante (sin tablas ni logos) y deja el cursor listo para el cuerpo.

    Portada APA 7 de estudiante: título, autor, afiliación (carrera,
    institución), curso, docente y fecha de entrega.
      - tarea: carpeta de la tarea; si se indica, `docente` y `fecha` se toman
        del README de la materia y de TAREA.md cuando no se pasan aquí.
      - fecha: str o datetime.date; por defecto la de entrega, o la de hoy.
      - indice: añade un índice automático tras la portada (APA no lo pide;
        úsalo solo si el docente lo exige).

    Devuelve (doc, figura, tabla) donde figura() ya tiene precargada la
    carpeta de capturas (por defecto: carpeta 'capturas' junto a `salida`).
    """
    salida = os.fspath(salida)
    if tarea is not None:
        docente_ficha, fecha_ficha = _desde_tarea(tarea)
        docente = docente or docente_ficha
        fecha = fecha or fecha_ficha
    if fecha is None or isinstance(fecha, datetime.date):
        fecha = fecha_portada(fecha)
    if carpeta_capturas is None:
        carpeta_capturas = os.path.join(os.path.dirname(os.path.abspath(salida)), "capturas")
    nombre = nombre or _cfg()["NOMBRE_ESTUDIANTE"]
    institucion = institucion or _cfg()["INSTITUCION"]
    carrera = carrera or _cfg()["CARRERA"]

    doc = Document()
    _estilos(doc)
    props = doc.core_properties
    props.title, props.author, props.subject = titulo, nombre, materia
    props.language = IDIOMA

    sec = doc.sections[0]
    sec.top_margin = sec.bottom_margin = Inches(1)
    sec.left_margin = sec.right_margin = Inches(1)
    _numero_de_pagina(sec)

    # ------------------------------- PORTADA -------------------------------
    for _ in range(3):
        parrafo(doc, "", sangria=False)
    parrafo(doc, titulo, alineacion=WD_ALIGN_PARAGRAPH.CENTER, sangria=False, negrita=True)
    parrafo(doc, "", sangria=False)
    afiliacion = ", ".join(x for x in (carrera, institucion) if x)
    for linea in (nombre, afiliacion, materia, docente, fecha):
        if linea:
            parrafo(doc, linea, alineacion=WD_ALIGN_PARAGRAPH.CENTER, sangria=False)
    salto_de_pagina(doc)

    if indice:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run("Índice")
        r.bold = True
        r.font.color.rgb = NEGRO
        campo = _campo(doc.add_paragraph(), 'TOC \\o "1-3" \\h \\z \\u',
                       "Actualiza el índice: clic derecho → Actualizar campo (F9).")
        doc.__dict__.setdefault("_rubric_driven", {})["indice"] = campo
        salto_de_pagina(doc)
        _actualizar_campos_al_abrir(doc)

    # El cuerpo empieza con el título en negrita; la introducción va sin
    # encabezado "Introducción", como pide APA 7.
    parrafo(doc, titulo, alineacion=WD_ALIGN_PARAGRAPH.CENTER, sangria=False, negrita=True)

    figura_fn = _make_figura(carpeta_capturas)
    return doc, figura_fn, tabla


def _actualizar_campos_al_abrir(doc):
    ajustes = doc.settings.element
    if ajustes.find(qn("w:updateFields")) is None:
        el = OxmlElement("w:updateFields")
        el.set(qn("w:val"), "true")
        ajustes.append(el)


def _rellenar_indice(doc):
    """Escribe los encabezados como contenido provisional del índice.

    Word recalcula el campo (con números de página) al abrir el documento,
    pero LibreOffice no lo hace al convertir a PDF; sin esto el PDF mostraría
    un índice vacío."""
    run = doc.__dict__.get("_rubric_driven", {}).get("indice")
    if run is None:
        return
    entradas = []
    for p in doc.paragraphs:
        m = re.fullmatch(r"Heading (\d)", p.style.name or "")
        if m and p.text.strip():
            entradas.append("    " * (int(m[1]) - 1) + p.text.strip())
    r = run._r
    fin = r[-1]  # el fldChar "end"
    for el in list(r):
        if el.tag in (qn("w:t"), qn("w:br")):
            r.remove(el)
    posicion = list(r).index(fin)
    nuevos = []
    for i, entrada in enumerate(entradas or ["(sin encabezados)"]):
        if i:
            nuevos.append(OxmlElement("w:br"))
        t = OxmlElement("w:t")
        t.set(qn("xml:space"), "preserve")
        t.text = entrada
        nuevos.append(t)
    for desplazamiento, el in enumerate(nuevos):
        r.insert(posicion + desplazamiento, el)


def guardar_documento(doc, salida):
    _rellenar_indice(doc)
    salida = os.fspath(salida)
    Path(salida).parent.mkdir(parents=True, exist_ok=True)
    doc.save(salida)
    print("Documento generado:", salida)
