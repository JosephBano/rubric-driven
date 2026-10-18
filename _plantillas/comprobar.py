# -*- coding: utf-8 -*-
"""Comprueba un entregable .docx contra la rúbrica de su TAREA.md.

No se fía de lo que diga el script ni el agente: abre el .docx generado y
mira qué hay de verdad.

  - cobertura: cada criterio debe tener una sección marcada con su ID
    (`titulo(..., criterios="C1")`), estar declarado como transversal, o como
    mínimo una sección cuyo título se le parezca (cobertura "probable");
  - proporción: la extensión de cada sección frente al peso del criterio;
  - extensión total frente a la que pide TAREA.md;
  - restos: capturas que faltan, secciones vacías, TODO, [COMPLETAR];
  - citas APA: cada cita del texto tiene su referencia y viceversa;
  - frescura: el .docx es más nuevo que generar_documento.py, el .pdf que el .docx.
"""
import datetime
import re
from dataclasses import dataclass, field
from pathlib import Path

import ficha
import rubrica as rub

TITULOS_REFERENCIAS = {"referencias", "referencias bibliograficas", "bibliografia", "references"}
_ANEXO = re.compile(r"^(anexo|apendice|apéndice|appendix)", re.I)
_PENDIENTE = re.compile(r"\[FALTA[^\]]*\]|\[COMPLETAR[^\]]*\]|\bTODO\b|\bPENDIENTE\b|lorem ipsum", re.I)
_PALABRA = re.compile(r"\w+(?:[-'’]\w+)*")
_ANIO = r"(?:(?:1[89]|20)\d{2}[a-z]?|s\.\s?f\.)"
_APELLIDO = r"[A-ZÁÉÍÓÚÑÜ][\wÁÉÍÓÚÑÜáéíóúñü'’-]+(?:\s(?:de|del|van|von|la)\s[A-ZÁÉÍÓÚÑ][\wáéíóúñ'’-]+)?"
_CITA_NARRATIVA = re.compile(rf"({_APELLIDO})(?:\set\sal\.|\s(?:y|e|&)\s{_APELLIDO})?\s\(({_ANIO})")
_PARENTESIS = re.compile(r"\(([^()]+)\)")
_PARTE_CITA = re.compile(rf"^(?:véase\s|ver\s|cf\.\s)?({_APELLIDO})(?:\set\sal\.|\s(?:y|e|&)\s.+?)?,\s({_ANIO})")
_PALABRAS_VACIAS = set(
    "para como sobre entre desde hasta donde cuando cada todo toda todos todas este esta estos "
    "estas ese esa con sin por los las del una uno unos unas que sus otro otra mediante "
    "correcto correcta correctamente adecuado adecuada adecuadamente claro clara claramente "
    "estudiante presenta explica describe realiza incluye elabora identifica muestra".split()
)

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def palabras(texto: str) -> int:
    return len(_PALABRA.findall(texto))


# --------------------------------------------------------------------------
# Análisis del .docx
# --------------------------------------------------------------------------
@dataclass
class Seccion:
    titulo: str
    nivel: int
    criterios: list = field(default_factory=list)
    palabras: int = 0
    figuras: int = 0
    tablas: int = 0
    anexo: bool = False
    referencias: bool = False

    @property
    def vacia(self) -> bool:
        return not (self.palabras or self.figuras or self.tablas)


@dataclass
class Analisis:
    secciones: list = field(default_factory=list)
    palabras_cuerpo: int = 0
    referencias: list = field(default_factory=list)
    hay_seccion_referencias: bool = False
    transversales: set = field(default_factory=set)
    pendientes: list = field(default_factory=list)   # (sección, texto)
    citas: list = field(default_factory=list)         # (apellido, año, contexto)


def _texto(p) -> str:
    return "".join(t.text or "" for t in p.iter(W + "t"))


def _estilo(p, estilos) -> str:
    ppr = p.find(W + "pPr")
    est = ppr.find(W + "pStyle") if ppr is not None else None
    return estilos.get(est.get(W + "val"), "") if est is not None else ""


def _nivel(p, estilos) -> int | None:
    nombre = _estilo(p, estilos).lower()
    m = re.match(r"(heading|título|titulo)\s*(\d)", nombre)
    if m:
        return int(m[2])
    ppr = p.find(W + "pPr")
    lvl = ppr.find(W + "outlineLvl") if ppr is not None else None
    if lvl is not None and lvl.get(W + "val", "9").isdigit() and int(lvl.get(W + "val")) < 9:
        return int(lvl.get(W + "val")) + 1
    return None


def _salto_de_pagina(p) -> bool:
    return any(br.get(W + "type") == "page" for br in p.iter(W + "br"))


def _citas(texto: str):
    for m in _CITA_NARRATIVA.finditer(texto):
        yield m[1], m[2].replace(" ", "")
    for m in _PARENTESIS.finditer(texto):
        for parte in m[1].split(";"):
            c = _PARTE_CITA.match(parte.strip())
            if c:
                yield c[1], c[2].replace(" ", "")


def analizar(ruta_docx: Path) -> Analisis:
    from docx import Document

    doc = Document(str(ruta_docx))
    estilos = {s.style_id: s.name for s in doc.styles}
    titulo_doc = (doc.core_properties.title or "").strip()
    a = Analisis()
    abiertas: list[Seccion] = []
    cuerpo = list(doc.element.body.iterchildren())

    # La portada termina en el primer salto de página (si lo hay).
    inicio = 0
    for i, el in enumerate(cuerpo):
        if el.tag == W + "p" and _salto_de_pagina(el):
            inicio = i + 1
            break

    en_indice = False
    titulo_visto = False
    for el in cuerpo[inicio:]:
        if el.tag == W + "tbl":
            for s in abiertas:
                s.tablas += 1
            continue
        if el.tag != W + "p":
            continue
        instr = " ".join(t.text or "" for t in el.iter(W + "instrText"))
        if "TOC" in instr:
            en_indice = True
        if en_indice:
            en_indice = not _salto_de_pagina(el)
            continue
        texto = _texto(el).strip()
        marcas = [b.get(W + "name", "") for b in el.iter(W + "bookmarkStart")]
        marcas = [m[len("rubrica_"):] for m in marcas if m.startswith("rubrica_")]
        for m in marcas:
            if m.endswith("_todo"):
                a.transversales.add(m[:-5].upper())
        marcas = [m.upper() for m in marcas if not m.endswith("_todo")]

        nivel = _nivel(el, estilos)
        if nivel is not None and texto:
            abiertas = [s for s in abiertas if s.nivel < nivel]
            padre_anexo = any(s.anexo for s in abiertas)
            s = Seccion(texto, nivel, marcas, anexo=padre_anexo or bool(_ANEXO.match(texto)))
            if nivel == 1 and rub.normalizar(texto) in TITULOS_REFERENCIAS:
                s.referencias = True
                a.hay_seccion_referencias = True
            a.secciones.append(s)
            abiertas.append(s)
            continue
        if marcas and abiertas:
            abiertas[-1].criterios += marcas

        if not titulo_visto and texto:
            titulo_visto = True
            if titulo_doc and texto == titulo_doc:
                continue  # el título repetido al inicio del cuerpo

        en_referencias = any(s.referencias for s in abiertas)
        if en_referencias:
            if texto:
                a.referencias.append(texto)
            continue
        n = palabras(texto)
        figuras = sum(1 for _ in el.iter(W + "drawing"))
        for s in abiertas:
            s.palabras += n
            s.figuras += figuras
        if not any(s.anexo for s in abiertas):
            a.palabras_cuerpo += n
        for m in _PENDIENTE.finditer(texto):
            a.pendientes.append((abiertas[-1].titulo if abiertas else "inicio", m[0]))
        for apellido, anio in _citas(texto):
            a.citas.append((apellido, anio, texto[:60]))
    return a


# --------------------------------------------------------------------------
# Cruce con la rúbrica
# --------------------------------------------------------------------------
def _raices(texto: str) -> set:
    return {w[:5] for w in re.findall(r"[a-z0-9]+", rub.normalizar(texto))
            if len(w) >= 4 and w not in _PALABRAS_VACIAS}


def _parecido(criterio: str, titulo: str) -> float:
    a, b = _raices(criterio), _raices(titulo)
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


@dataclass
class Cobertura:
    criterio: rub.Criterio
    modo: str | None = None          # marcado | transversal | referencias | probable | None
    secciones: list = field(default_factory=list)
    palabras: int = 0
    figuras: int = 0
    tablas: int = 0
    esperado: int | None = None

    @property
    def cubierto(self) -> bool:
        return self.modo is not None

    @property
    def ratio(self) -> float | None:
        if not self.esperado:
            return None
        return self.palabras / self.esperado

    def donde(self) -> str:
        if self.modo is None:
            return "SIN CUBRIR"
        if self.modo == "transversal":
            return "todo el documento"
        nombres = "; ".join(s.titulo for s in self.secciones)
        if self.modo == "referencias":
            return nombres
        texto = f"{nombres} ({self.palabras} pal."
        texto += f", {self.figuras} fig." if self.figuras else ""
        texto += f", {self.tablas} tabla{'s' if self.tablas > 1 else ''}" if self.tablas else ""
        texto += ")"
        return texto + (" — probable, sin marcar" if self.modo == "probable" else "")


def cruzar(criterios: list, a: Analisis) -> list:
    coberturas = []
    for c in criterios:
        cob = Cobertura(c)
        marcadas = [s for s in a.secciones if c.id in s.criterios]
        if marcadas:
            cob.modo = "referencias" if all(s.referencias for s in marcadas) else "marcado"
            cob.secciones = marcadas
        elif c.id in a.transversales:
            cob.modo = "transversal"
        else:
            candidatas = [(round(_parecido(c.texto, s.titulo), 2), s) for s in a.secciones
                          if not s.criterios]
            candidatas = [x for x in candidatas if x[0] >= 0.5]
            if candidatas:
                cob.modo = "probable"
                cob.secciones = [max(candidatas, key=lambda x: x[0])[1]]
        for s in cob.secciones:
            # Una sección que cubre varios criterios reparte su extensión.
            compartida = max(1, len(s.criterios))
            cob.palabras += s.palabras // compartida
            cob.figuras += s.figuras
            cob.tablas += s.tablas
        coberturas.append(cob)

    # Reparto esperado de la extensión según el peso de cada criterio.
    con_seccion = [c for c in coberturas if c.modo in ("marcado", "probable")]
    if con_seccion:
        pesos = [c.criterio.puntaje for c in con_seccion]
        if any(p is None for p in pesos):
            pesos = [1.0] * len(con_seccion)
        total_pesos = sum(pesos) or 1.0
        total_palabras = sum(c.palabras for c in con_seccion)
        for c, peso in zip(con_seccion, pesos):
            c.esperado = round(total_palabras * peso / total_pesos)
    return coberturas


# --------------------------------------------------------------------------
# Informe
# --------------------------------------------------------------------------
@dataclass
class Informe:
    docx: Path | None
    coberturas: list = field(default_factory=list)
    errores: list = field(default_factory=list)
    avisos: list = field(default_factory=list)
    analisis: Analisis | None = None

    @property
    def ok(self) -> bool:
        return not self.errores

    @property
    def puntos(self) -> tuple[float, float]:
        total = sum(c.criterio.puntaje or 0 for c in self.coberturas)
        cubiertos = sum(c.criterio.puntaje or 0 for c in self.coberturas if c.cubierto)
        return cubiertos, total


def buscar_docx(carpeta: Path) -> Path | None:
    candidatos = [p for p in Path(carpeta).glob("*.docx") if not p.name.startswith("~$")]
    if not candidatos:
        return None
    propios = [p for p in candidatos if p.name.startswith(Path(carpeta).name + "_")]
    return max(propios or candidatos, key=lambda p: p.stat().st_mtime)


def _coincide(apellido: str, anio: str, referencia: str) -> bool:
    """¿La entrada de referencias empieza por ese autor y lleva ese año?"""
    entrada = rub.normalizar(referencia.lstrip("*"))
    return (entrada.startswith(rub.normalizar(apellido))
            and re.search(r"\(" + re.escape(anio.lower()), entrada) is not None)


def comprobar(carpeta: Path, docx: Path | None = None, hoy: datetime.date | None = None) -> Informe:
    carpeta = Path(carpeta).resolve()
    tarea = ficha.leer_tarea(carpeta)
    criterios = rub.leer(tarea.ruta)
    docx = Path(docx) if docx else buscar_docx(carpeta)
    inf = Informe(docx)

    if not criterios:
        inf.errores.append("TAREA.md no tiene rúbrica: añade los criterios a la tabla "
                           "(o `tareas.py rubrica --importar <archivo.docx>`).")
    if docx is None or not docx.exists():
        inf.errores.append("No hay ningún .docx generado en la carpeta: ejecuta "
                           "`tareas.py generar`.")
        return inf

    a = inf.analisis = analizar(docx)
    inf.coberturas = cruzar(criterios, a)

    for cob in inf.coberturas:
        c = cob.criterio
        if not cob.cubierto:
            inf.errores.append(f"{c.id} sin cubrir: «{c.texto}». Márcalo con "
                               f"titulo(doc, ..., criterios=\"{c.id}\") o transversal(doc, \"{c.id}\").")
            continue
        if cob.modo == "probable":
            inf.avisos.append(f"{c.id} se asoció por el título a «{cob.secciones[0].titulo}»; "
                              f"márcalo con criterios=\"{c.id}\" para que sea seguro.")
        if cob.modo in ("marcado", "probable") and all(s.vacia for s in cob.secciones):
            inf.errores.append(f"{c.id}: la sección «{cob.secciones[0].titulo}» está vacía.")
        elif cob.ratio is not None and cob.ratio < 0.5:
            inf.avisos.append(f"{c.id} poco desarrollado: {cob.palabras} palabras frente a "
                              f"~{cob.esperado} según su peso ({formato_puntaje(c)}).")
        elif cob.ratio is not None and cob.ratio > 2.0 and cob.palabras > 150:
            inf.avisos.append(f"{c.id} desproporcionado: {cob.palabras} palabras frente a "
                              f"~{cob.esperado} según su peso ({formato_puntaje(c)}).")

    ids = {c.id for c in criterios}
    marcados = {i for s in a.secciones for i in s.criterios} | a.transversales
    for extra in sorted(marcados - ids):
        inf.avisos.append(f"El documento marca {extra}, que no está en la rúbrica de TAREA.md.")

    for s in a.secciones:
        if s.vacia and not s.referencias and not s.criterios:
            inf.avisos.append(f"La sección «{s.titulo}» está vacía.")
    for seccion, texto in a.pendientes:
        inf.errores.append(f"Contenido pendiente en «{seccion}»: {texto}")

    if tarea.extension:
        if a.palabras_cuerpo < 0.8 * tarea.extension:
            inf.avisos.append(f"Extensión corta: {a.palabras_cuerpo} palabras frente a "
                              f"~{tarea.extension} que pide TAREA.md.")
        elif a.palabras_cuerpo > 1.25 * tarea.extension:
            inf.avisos.append(f"Extensión larga: {a.palabras_cuerpo} palabras frente a "
                              f"~{tarea.extension} que pide TAREA.md.")

    # Citas y referencias
    if a.citas and not a.hay_seccion_referencias:
        inf.errores.append(f"Hay {len(a.citas)} citas en el texto pero no hay sección Referencias.")
    elif a.hay_seccion_referencias:
        if not a.referencias:
            inf.avisos.append("La sección Referencias está vacía.")
        huerfanas = sorted({(ap, an) for ap, an, _ in a.citas
                            if not any(_coincide(ap, an, r) for r in a.referencias)})
        for ap, an in huerfanas:
            inf.errores.append(f"Cita sin referencia: {ap} ({an}).")
        for r in a.referencias:
            if not any(_coincide(ap, an, r) for ap, an, _ in a.citas):
                inf.avisos.append(f"Referencia que no se cita en el texto: {r[:70]}")

    # Frescura de los archivos
    script = carpeta / "generar_documento.py"
    if script.exists() and script.stat().st_mtime > docx.stat().st_mtime + 1:
        inf.avisos.append("generar_documento.py es más reciente que el .docx: regenéralo.")
    pdf = docx.with_suffix(".pdf")
    if pdf.exists() and pdf.stat().st_mtime + 1 < docx.stat().st_mtime:
        inf.avisos.append("El .pdf es más antiguo que el .docx: vuelve a convertirlo.")

    hoy = hoy or datetime.date.today()
    if tarea.fecha and tarea.fecha < hoy and tarea.estado == "pendiente":
        inf.avisos.append(f"La fecha de entrega ({tarea.fecha}) ya pasó y la tarea sigue pendiente.")
    return inf


def formato_puntaje(c: rub.Criterio) -> str:
    return f"{rub.formatear_puntaje(c.puntaje)} pts" if c.puntaje is not None else "sin puntaje"


def actualizar_tarea(carpeta: Path, inf: Informe) -> None:
    """Rellena la columna 'Dónde se cumple' de TAREA.md con lo comprobado."""
    criterios = [cob.criterio for cob in inf.coberturas]
    for cob in inf.coberturas:
        cob.criterio.donde = cob.donde()
    if criterios:
        rub.escribir(Path(carpeta) / "TAREA.md", criterios)


def imprimir(inf: Informe, carpeta: Path) -> None:
    print(f"Comprobación de {Path(carpeta).name}")
    if inf.docx:
        print(f"  Documento: {inf.docx.name}")
    if inf.analisis:
        a = inf.analisis
        print(f"  Cuerpo: {a.palabras_cuerpo} palabras, {len(a.secciones)} secciones, "
              f"{len(a.citas)} citas, {len(a.referencias)} referencias")
    if inf.coberturas:
        print("\n  Rúbrica")
        ancho = max(len(c.criterio.id) for c in inf.coberturas)
        for cob in inf.coberturas:
            c = cob.criterio
            marca = {"marcado": "[ok]   ", "transversal": "[ok]   ", "referencias": "[ok]   ",
                     "probable": "[~]    ", None: "[falta]"}[cob.modo]
            peso = formato_puntaje(c)
            print(f"  {marca} {c.id:<{ancho}}  {c.texto[:48]:<48}  {peso:>9}  → {cob.donde()}")
        cubiertos, total = inf.puntos
        if total:
            print(f"\n  Puntos con sección que los cubre: {rub.formatear_puntaje(cubiertos)} "
                  f"de {rub.formatear_puntaje(total)}")
    for e in inf.errores:
        print("  [error] " + e)
    for w in inf.avisos:
        print("  [aviso] " + w)
    if inf.ok and not inf.avisos:
        print("  Todo en orden.")
