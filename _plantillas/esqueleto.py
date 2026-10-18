# -*- coding: utf-8 -*-
"""Convierte la rúbrica de TAREA.md en el esqueleto de secciones de
generar_documento.py: una sección por criterio, marcada con su ID, y una
extensión orientativa proporcional a su puntaje.
"""
import re
from pathlib import Path

import rubrica as rub

INICIO = "# --- secciones (tareas.py esqueleto reescribe este bloque) ---"
FIN = "# --- fin de secciones ---"
PALABRAS_POR_DEFECTO = 1500
PARTE_INTRO = PARTE_CONCLUSION = 0.10

_INTRO = re.compile(r"introducci", re.I)
_CONCLUSION = re.compile(r"conclusi", re.I)


_CONECTORES = set("y e o u de del la el los las lo un una sus su con en a al para por que como".split())


def titulo_de(criterio: str, max_palabras: int = 9) -> str:
    """'Explica el uso de índices: tipos y ventajas.' → 'Explica el uso de índices'.
    Recorta frases largas sin dejarlas colgando en 'y', 'de', 'sus'..."""
    texto = re.split(r"[:.;(\n]", criterio.strip())[0].strip() or criterio.strip()
    palabras = texto.split()
    if len(palabras) > max_palabras:
        palabras = palabras[:max_palabras]
        while len(palabras) > 3 and palabras[-1].lower() in _CONECTORES:
            palabras.pop()
        texto = " ".join(palabras)
    return texto[:1].upper() + texto[1:]


def _cabecera(c: rub.Criterio, porcentaje: float | None, palabras: int | None) -> str:
    partes = [c.id, c.texto]
    if c.puntaje is not None:
        partes.append(f"{rub.formatear_puntaje(c.puntaje)} pts"
                      + (f" ({porcentaje:.0f} %)" if porcentaje is not None else ""))
    if palabras:
        partes.append(f"~{palabras} palabras")
    return "# " + " · ".join(partes)


def bloque(criterios: list, total_palabras: int | None = None) -> tuple[str, str]:
    """Devuelve (bloque de secciones, IDs que cubre la sección Referencias)."""
    total = total_palabras or PALABRAS_POR_DEFECTO
    transversales = [c for c in criterios if c.transversal]
    de_refs = [c for c in criterios if c.de_referencias]
    intro = [c for c in criterios if _INTRO.search(c.texto) and c not in transversales]
    concl = [c for c in criterios if _CONCLUSION.search(c.texto) and c not in transversales + intro]
    cuerpo = [c for c in criterios if c not in transversales + de_refs + intro + concl]

    suma = sum(c.puntaje or 0 for c in criterios) or None
    pesos = [c.puntaje for c in cuerpo]
    if any(p is None for p in pesos):
        pesos = [1.0] * len(cuerpo)
    total_pesos = sum(pesos) or 1.0
    presupuesto = total * (1 - PARTE_INTRO - PARTE_CONCLUSION)

    def pct(c):
        return 100 * c.puntaje / suma if suma and c.puntaje is not None else None

    L = [INICIO, f"# Extensión orientativa total: ~{total} palabras. Cambia los títulos con"
                 " libertad: lo que cuenta es el ID de criterios=."]
    if intro:
        for c in intro:
            L += [_cabecera(c, pct(c), round(total * PARTE_INTRO)),
                  f"titulo(doc, \"Introducción\", 1, criterios={c.id!r})", 'parrafo(doc, "")', ""]
    else:
        L += [f"# Introducción (APA 7: sin encabezado) · ~{round(total * PARTE_INTRO)} palabras",
              'parrafo(doc, "")', ""]
    for c, peso in zip(cuerpo, pesos):
        L += [_cabecera(c, pct(c), round(presupuesto * peso / total_pesos)),
              f"titulo(doc, {titulo_de(c.texto)!r}, 1, criterios={c.id!r})",
              'parrafo(doc, "")', ""]
    concl_ids = " ".join(c.id for c in concl)
    for c in concl:
        L.append(_cabecera(c, pct(c), None))
    L += [f"# Conclusiones · ~{round(total * PARTE_CONCLUSION)} palabras",
          f"titulo(doc, \"Conclusiones\", 1{', criterios=' + repr(concl_ids) if concl else ''})",
          'parrafo(doc, "")', ""]
    if transversales:
        L.append("# Criterios que se cumplen en todo el documento:")
        L += [_cabecera(c, pct(c), None) for c in transversales]
        L += [f"transversal(doc, {', '.join(repr(c.id) for c in transversales)})", ""]
    L.append(FIN)
    return "\n".join(L) + "\n", " ".join(c.id for c in de_refs)


def aplicar(script: Path, criterios: list, total_palabras: int | None = None,
            forzar: bool = False) -> None:
    """Sustituye el bloque de secciones de generar_documento.py.

    Si el bloque ya tiene texto escrito no lo toca salvo con forzar=True, y
    entonces guarda antes una copia .bak. Con secciones aún vacías se puede
    volver a ejecutar sin miedo (p. ej. si cambia la rúbrica).
    """
    texto = script.read_text(encoding="utf-8")
    if INICIO not in texto or FIN not in texto:
        raise ValueError(f"{script.name} no tiene el bloque de secciones (marcas «{INICIO}» y "
                         f"«{FIN}»); añádelas o vuelve a crear el script desde la plantilla.")
    antes, resto = texto.split(INICIO, 1)
    actual, despues = resto.split(FIN, 1)
    if _tiene_texto(actual):
        if not forzar:
            raise FileExistsError("generar_documento.py ya tiene texto en sus secciones; usa "
                                  "--forzar para reescribirlas (se guarda una copia .bak).")
        script.with_suffix(".py.bak").write_text(texto, encoding="utf-8")

    nuevo, refs = bloque(criterios, total_palabras)
    if refs:
        despues = re.sub(r"referencias\(doc, bib[^)]*\)",
                         f"referencias(doc, bib, criterios={refs!r})", despues, count=1)
    script.write_text(antes + nuevo + "\n" + despues.lstrip("\n"), encoding="utf-8")


def _tiene_texto(bloque_: str) -> bool:
    """¿Hay contenido escrito (algo más que parrafo(doc, "") y títulos)?"""
    for linea in bloque_.splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or linea.startswith(("titulo(", "transversal(")):
            continue
        if re.fullmatch(r"""parrafo\(doc,\s*(""|'')\s*\)""", linea):
            continue
        return True
    return False
