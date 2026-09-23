# -*- coding: utf-8 -*-
"""
Plantilla reutilizable para generar informes .docx en normas APA 7,
monocromáticos (texto e imágenes en blanco y negro).

Los datos del estudiante (portada y sufijo de archivos) se leen del .env de
la raíz del repositorio; sin él, importar este módulo termina con un error
que explica cómo crearlo.

Uso típico en el script de una actividad (lo genera `tareas.py tarea`):

    import sys
    from pathlib import Path
    AQUI = Path(__file__).resolve().parent
    sys.path.insert(0, str(AQUI.parents[2] / "_plantillas"))  # materias/<materia>/<tarea>/
    from apa_docx import *

    salida = AQUI / nombre_entregable("A15_Titulo_Corto")   # + sufijo del .env
    doc, figura, tabla = nuevo_documento(
        titulo="Título del Informe",
        materia="Nombre de la Materia",
        salida=salida,
    )

    titulo(doc, "Introducción", 2)
    parrafo(doc, "Texto del párrafo...")
    vinieta(doc, "Punto de una lista.")
    codigo(doc, "$ comando de ejemplo")
    figura(doc, 1, "Descripción de la figura", "capturas/fig1.png", "Nota explicativa.")
    tabla(doc, 1, "Descripción de la tabla", ["Col A", "Col B"], [("x", "y")])
    referencia(doc, "Autor, A. (2026). Título. Editorial.")

    doc.save(salida)  # o guardar_documento(doc, salida)

Ver también PLANTILLA_README.md en esta misma carpeta.
"""
import datetime
import os
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from config import cargar_o_salir

NEGRO = RGBColor(0, 0, 0)

# --------------------------------------------------------------------------
# Datos del estudiante: se leen del .env de la raíz del repositorio
# --------------------------------------------------------------------------
_CONFIG = cargar_o_salir()
NOMBRE_ESTUDIANTE = _CONFIG["NOMBRE_ESTUDIANTE"]
INSTITUCION = _CONFIG["INSTITUCION"]
CARRERA = _CONFIG["CARRERA"]
SUFIJO_ARCHIVOS = _CONFIG["SUFIJO_ARCHIVOS"]

_MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
          "agosto", "septiembre", "octubre", "noviembre", "diciembre")


def fecha_hoy():
    """Fecha de hoy en formato de portada: '23 de septiembre de 2026'."""
    hoy = datetime.date.today()
    return f"{hoy.day} de {_MESES[hoy.month - 1]} de {hoy.year}"


def nombre_entregable(base, extension=".docx"):
    """'A15_Titulo' -> 'A15_Titulo_<SUFIJO_ARCHIVOS>.docx'."""
    return f"{base}_{SUFIJO_ARCHIVOS}{extension}"


# --------------------------------------------------------------------------
# Utilidades de bajo nivel
# --------------------------------------------------------------------------
def _numero_de_pagina(section):
    p = section.header.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = p.add_run()
    for instr, tipo in ((None, "begin"), ("PAGE", "instrText"), (None, "end")):
        el = OxmlElement("w:fldChar") if tipo != "instrText" else OxmlElement("w:instrText")
        if tipo == "instrText":
            el.set(qn("xml:space"), "preserve")
            el.text = " PAGE "
        else:
            el.set(qn("w:fldCharType"), tipo)
        run._r.append(el)
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)
    run.font.color.rgb = NEGRO


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


def titulo(doc, texto, nivel=1):
    """nivel 1: encabezado centrado y negrita (secciones principales).
    nivel 2/3: encabezado alineado a la izquierda (nivel 3 en cursiva)."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER if nivel == 1 else WD_ALIGN_PARAGRAPH.LEFT
    pf = p.paragraph_format
    pf.line_spacing = 2.0
    pf.space_before = Pt(12 if nivel == 1 else 10)
    pf.space_after = Pt(0)
    pf.keep_with_next = True
    r = p.add_run(texto)
    r.bold = True
    r.italic = (nivel == 3)
    r.font.size = Pt(12)
    r.font.color.rgb = NEGRO
    return p


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
        r = p.add_run(linea if linea.strip() else " ")
        r.font.name = "Courier New"
        r._element.rPr.rFonts.set(qn("w:eastAsia"), "Courier New")
        r.font.size = Pt(tamano)
        r.font.color.rgb = NEGRO


def referencia(doc, texto):
    """Entrada de la lista de referencias con sangría francesa."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pf = p.paragraph_format
    pf.line_spacing = 2.0
    pf.left_indent = Inches(0.5)
    pf.first_line_indent = Inches(-0.5)
    pf.space_after = Pt(0)
    r = p.add_run(texto)
    r.font.size = Pt(12)
    r.font.color.rgb = NEGRO


def _make_figura(carpeta_capturas):
    """Genera la función figura() con la carpeta de capturas ya fijada."""
    def figura(doc, numero, descripcion, archivo, nota, ancho=5.5):
        p = doc.add_paragraph()
        p.paragraph_format.line_spacing = 2.0
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.keep_with_next = True
        r = p.add_run("Figura %d" % numero)
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

        ruta = archivo if os.path.isabs(archivo) else os.path.join(carpeta_capturas, archivo)
        if os.path.exists(ruta):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(6)
            p.paragraph_format.line_spacing = 1.0
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
    return figura


def tabla(doc, numero, descripcion, encabezados, filas):
    """Tabla genérica en formato APA (Tabla N + descripción en cursiva +
    tabla con bordes finos, encabezado sombreado en gris claro).
    encabezados: lista de strings. filas: lista de tuplas del mismo largo."""
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 2.0
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.keep_with_next = True
    r = p.add_run("Tabla %d" % numero)
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
        r = celda.paragraphs[0].add_run(texto)
        r.bold = True
        r.font.size = Pt(10.5)
        r.font.color.rgb = NEGRO

    for fila in filas:
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
# Punto de entrada: crea el documento con portada y estilos ya aplicados
# --------------------------------------------------------------------------
def nuevo_documento(*, titulo, materia, salida, fecha=None,
                     carpeta_capturas=None, nombre=NOMBRE_ESTUDIANTE,
                     institucion=INSTITUCION, carrera=CARRERA):
    """Crea el Document(), aplica estilos APA/monocromáticos, arma la
    portada (sin tablas ni logos) y deja el cursor listo para el cuerpo.

    Devuelve (doc, figura, tabla_fn) donde figura() ya tiene precargada la
    carpeta de capturas (por defecto: carpeta 'capturas' junto a `salida`).
    Guardar al final con doc.save(salida).
    """
    salida = os.fspath(salida)
    if fecha is None:
        fecha = fecha_hoy()
    if carpeta_capturas is None:
        carpeta_capturas = os.path.join(os.path.dirname(os.path.abspath(salida)), "capturas")

    doc = Document()

    est = doc.styles["Normal"]
    est.font.name = "Times New Roman"
    est.font.size = Pt(12)
    est.font.color.rgb = NEGRO
    est.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")

    sec = doc.sections[0]
    sec.top_margin = sec.bottom_margin = Inches(1)
    sec.left_margin = sec.right_margin = Inches(1)
    _numero_de_pagina(sec)

    # ------------------------------- PORTADA -------------------------------
    for _ in range(4):
        parrafo(doc, "", sangria=False)

    parrafo(doc, titulo, alineacion=WD_ALIGN_PARAGRAPH.CENTER, sangria=False, negrita=True)
    parrafo(doc, "", sangria=False)
    parrafo(doc, nombre, alineacion=WD_ALIGN_PARAGRAPH.CENTER, sangria=False)
    parrafo(doc, institucion, alineacion=WD_ALIGN_PARAGRAPH.CENTER, sangria=False)
    parrafo(doc, carrera, alineacion=WD_ALIGN_PARAGRAPH.CENTER, sangria=False)
    parrafo(doc, materia, alineacion=WD_ALIGN_PARAGRAPH.CENTER, sangria=False)
    parrafo(doc, fecha, alineacion=WD_ALIGN_PARAGRAPH.CENTER, sangria=False)

    doc.add_page_break()

    parrafo(doc, titulo, alineacion=WD_ALIGN_PARAGRAPH.CENTER, sangria=False, negrita=True)

    figura_fn = _make_figura(carpeta_capturas)
    return doc, figura_fn, tabla


def guardar_documento(doc, salida):
    salida = os.fspath(salida)
    doc.save(salida)
    print("Documento generado:", salida)
