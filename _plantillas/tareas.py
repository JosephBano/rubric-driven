#!/usr/bin/env python3
"""rubric-driven: materias, tareas, rúbricas, comprobación y PDF.

Uso (desde la raíz del repositorio):
    python _plantillas/tareas.py verificar
    python _plantillas/tareas.py materia <carpeta> "<Nombre de la materia>"
    python _plantillas/tareas.py tarea <materia> <codigo> "<Título>" [--tipo T]
    python _plantillas/tareas.py rubrica <tarea> [--importar archivo.docx]
    python _plantillas/tareas.py esqueleto <tarea> [--palabras N] [--forzar]
    python _plantillas/tareas.py generar <tarea> [--sin-pdf]
    python _plantillas/tareas.py comprobar <tarea> [--actualizar]
    python _plantillas/tareas.py pdf <archivo.docx | carpeta>
    python _plantillas/tareas.py estado [<materia>]
    python _plantillas/tareas.py marcar <tarea> <pendiente|lista|entregada>

Ejemplos:
    python _plantillas/tareas.py materia programacion-web-2 "Programación Web 2"
    python _plantillas/tareas.py tarea sgbd1 A15 "Procedimientos almacenados"
    python _plantillas/tareas.py rubrica materias/sgbd1/A15_Procedimientos_Almacenados \\
        --importar enunciado/rubrica.docx
    python _plantillas/tareas.py esqueleto materias/sgbd1/A15_Procedimientos_Almacenados
    python _plantillas/tareas.py generar materias/sgbd1/A15_Procedimientos_Almacenados

Las materias se crean siempre dentro de materias/; <materia> es solo el nombre
de su carpeta (sgbd1), no la ruta. <tarea> es la ruta a la carpeta de la tarea.
"""
import argparse
import datetime
import importlib.util
import os
import re
import shutil
import signal
import subprocess
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import RAIZ, ConfigError, cargar, cargar_o_salir  # noqa: E402
import comprobar as comp  # noqa: E402
import esqueleto as esq  # noqa: E402
import ficha  # noqa: E402
import rubrica as rub  # noqa: E402

PLANTILLAS = RAIZ / "_plantillas"
MATERIAS = RAIZ / "materias"
TIPOS = {
    "actividad": "Actividad (A)",
    "practica": "Práctico-experimental (P)",
    "evaluacion": "Evaluación (E)",
    "otro": "Otro",
}
ESTADOS = ("pendiente", "lista", "entregada")

# LibreOffice: temporales en disco (no en el tmpfs de /tmp) y tope de 2 GB por
# archivo escrito; un .docx mal formado puede hacer que soffice llene el disco.
LO_TMP = Path.home() / ".cache" / "lo-tmp"
LO_PERFIL = Path.home() / ".cache" / "lo-perfil"
LO_LIMITE_BYTES = 2 * 1024**3
LO_TIMEOUT = 300


# --------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------
def slug_titulo(titulo: str) -> str:
    """'Procedimientos almacenados' -> 'Procedimientos_Almacenados' (sin tildes)."""
    sin_tildes = unicodedata.normalize("NFKD", titulo).encode("ascii", "ignore").decode()
    palabras = re.findall(r"[A-Za-z0-9]+", sin_tildes)
    return "_".join(p[:1].upper() + p[1:] for p in palabras)


def tipo_por_codigo(codigo: str) -> str:
    return {"A": "actividad", "P": "practica", "E": "evaluacion"}.get(codigo[:1].upper(), "otro")


def rellenar(plantilla: Path, **valores) -> str:
    texto = plantilla.read_text(encoding="utf-8")
    for clave, valor in valores.items():
        texto = texto.replace("{" + clave + "}", valor)
    return texto


def ruta_relativa(ruta: Path) -> str:
    ruta = Path(ruta).resolve()
    return ruta.relative_to(RAIZ).as_posix() if ruta.is_relative_to(RAIZ) else str(ruta)


def carpeta_tarea(texto: str) -> Path:
    """Admite la ruta completa o relativa a la raíz o a materias/."""
    for candidata in (Path(texto), RAIZ / texto, MATERIAS / texto):
        if (candidata / "TAREA.md").exists():
            return candidata.resolve()
    sys.exit(f"No encuentro la tarea '{texto}' (debe ser una carpeta con TAREA.md).")


def git(*args, check=True, capturar=False):
    return subprocess.run(
        ["git", *args], cwd=RAIZ, check=check, text=True, capture_output=capturar,
    )


def python_del_repo() -> str:
    venv = RAIZ / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    return str(venv) if venv.exists() else sys.executable


# --------------------------------------------------------------------------
# verificar, materia, tarea
# --------------------------------------------------------------------------
def cmd_verificar(_args) -> None:
    ok = True

    def informe(bien: bool, texto: str) -> None:
        nonlocal ok
        ok &= bien
        print(("  [ok]    " if bien else "  [falta] ") + texto)

    print("Configuración")
    try:
        cfg = cargar()
        informe(True, f".env cargado ({cfg['NOMBRE_ESTUDIANTE']})")
    except ConfigError as e:
        informe(False, str(e).replace("\n", "\n          "))

    print("Python")
    en_venv = Path(sys.prefix).resolve() == (RAIZ / ".venv").resolve()
    informe(en_venv, "ejecutando con .venv de la raíz" if en_venv
            else f"no se está usando .venv (usa .venv/bin/python); intérprete: {sys.executable}")
    for modulo, paquete in (("docx", "python-docx"), ("PIL", "Pillow")):
        informe(importlib.util.find_spec(modulo) is not None, f"{paquete} instalado")

    print("LibreOffice")
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    informe(bool(soffice), soffice or "no instalado: sin él no se generan los PDF")

    print("Repositorio público")
    permitidos = (".gitignore", ".env.example", "README.md", "AGENTS.md", "LICENSE",
                  "requirements.txt", "_plantillas/", "tests/", ".github/")
    r = git("ls-files", check=False, capturar=True)
    if r.returncode != 0:
        print("  [--]    no es un repositorio git; no se comprueba")
    else:
        fuera = [f for f in r.stdout.splitlines() if not f.startswith(permitidos)]
        informe(not fuera, "solo plantillas y documentación en git" if not fuera
                else "archivos de materias en el repo público: " + ", ".join(fuera[:5]))

    sys.exit(0 if ok else 1)


def cmd_materia(args) -> None:
    cargar_o_salir()
    if "/" in args.carpeta or "\\" in args.carpeta:
        sys.exit("Indica solo el nombre de la carpeta (p. ej. sgbd2); se crea dentro de materias/.")
    destino = MATERIAS / args.carpeta
    if destino.exists():
        sys.exit(f"Ya existe: materias/{args.carpeta}/")
    destino.mkdir(parents=True)
    (destino / "README.md").write_text(
        rellenar(PLANTILLAS / "materia" / "README.md", materia_nombre=args.nombre),
        encoding="utf-8",
    )
    print(f"Materia creada: materias/{args.carpeta}/")
    print("  Completa en su README.md el docente, la plataforma y las reglas de entrega.")


def cmd_tarea(args) -> None:
    cargar_o_salir()
    nombre_carpeta = Path(args.materia).name  # admite "sgbd1" o "materias/sgbd1"
    carpeta_materia = MATERIAS / nombre_carpeta
    if not carpeta_materia.is_dir():
        existentes = ", ".join(sorted(p.name for p in MATERIAS.iterdir() if p.is_dir())) if MATERIAS.is_dir() else "ninguna"
        sys.exit(f"No existe la materia '{nombre_carpeta}' en materias/ (hay: {existentes}).\n"
                 f"  Créala con: tareas.py materia {nombre_carpeta} \"Nombre\"")
    codigo = args.codigo.upper()
    tipo = args.tipo or tipo_por_codigo(codigo)
    base = f"{codigo}_{slug_titulo(args.titulo)}"
    destino = carpeta_materia / base
    if destino.exists():
        sys.exit(f"Ya existe: {ruta_relativa(destino)}")

    materia_nombre = ficha.leer_materia(carpeta_materia).nombre
    ruta_carpeta = ruta_relativa(destino)
    destino.mkdir()
    (destino / "enunciado").mkdir()
    (destino / "capturas").mkdir()
    (destino / "TAREA.md").write_text(
        rellenar(PLANTILLAS / "tarea" / "TAREA.md", codigo=codigo, titulo=args.titulo,
                 materia_nombre=materia_nombre, tipo=TIPOS[tipo]),
        encoding="utf-8",
    )
    (destino / "generar_documento.py").write_text(
        rellenar(PLANTILLAS / "tarea" / "generar_documento.py", codigo=codigo,
                 titulo=args.titulo, titulo_py=repr(args.titulo),
                 materia_py=repr(materia_nombre), base=base, ruta_carpeta=ruta_carpeta),
        encoding="utf-8",
    )

    readme = carpeta_materia / "README.md"
    if readme.exists():
        texto = readme.read_text(encoding="utf-8")
        if "| Carpeta | Entrega | Estado |" in texto:
            fila = f"| `{base}` | {codigo} — {ficha.escapar_celda(args.titulo)} | pendiente |\n"
            readme.write_text(texto.rstrip("\n") + "\n" + fila, encoding="utf-8")

    print(f"Tarea creada: {ruta_carpeta}/")
    print("  1. Deja el enunciado y la RÚBRICA del docente en enunciado/.")
    print(f"  2. Pasa la rúbrica a TAREA.md (tareas.py rubrica {ruta_carpeta} --importar <rubrica.docx>)")
    print("     y completa la fecha, la extensión y el formato.")
    print(f"  3. tareas.py esqueleto {ruta_carpeta}   → una sección por criterio")
    print(f"  4. Escribe el contenido y ejecuta: tareas.py generar {ruta_carpeta}")


# --------------------------------------------------------------------------
# rubrica, esqueleto
# --------------------------------------------------------------------------
def cmd_rubrica(args) -> None:
    carpeta = carpeta_tarea(args.tarea)
    tarea_md = carpeta / "TAREA.md"
    if args.importar:
        origen = Path(args.importar)
        if not origen.is_absolute() and not origen.exists():
            origen = carpeta / origen
        if not origen.exists():
            sys.exit(f"No existe {args.importar}")
        if origen.suffix.lower() != ".docx":
            sys.exit("Solo se importan rúbricas en .docx. Para un PDF o una imagen, copia los "
                     "criterios a la tabla de TAREA.md (o pídeselo al agente).")
        criterios = rub.importar_docx(origen)
        if not criterios:
            sys.exit(f"No encontré ninguna tabla de rúbrica en {origen.name}.")
        existentes = rub.leer(tarea_md)
        if existentes and not args.forzar:
            sys.exit(f"TAREA.md ya tiene {len(existentes)} criterios; usa --forzar para sustituirlos.")
        rub.escribir(tarea_md, criterios)
        print(f"Importados {len(criterios)} criterios de {origen.name} a TAREA.md. Revísalos.")

    criterios = rub.leer(tarea_md)
    if not criterios:
        sys.exit("TAREA.md no tiene rúbrica todavía: rellena la tabla de la sección Rúbrica "
                 "o usa --importar <rubrica.docx>.")
    total = sum(c.puntaje or 0 for c in criterios)
    ancho = max(len(c.id) for c in criterios)
    for c in criterios:
        pct = f"{100 * c.puntaje / total:4.0f} %" if total and c.puntaje is not None else "     "
        tipo = " (transversal)" if c.transversal else " (referencias)" if c.de_referencias else ""
        print(f"  {c.id:<{ancho}}  {comp.formato_puntaje(c):>9}  {pct}  {c.texto}{tipo}")
    print(f"  Total: {rub.formatear_puntaje(total)} pts" if total else
          "  Sin puntajes: el reparto de extensión será a partes iguales.")
    if any(re.fullmatch(r"C\d+", c.id) is None for c in criterios):
        print("  (IDs propios: úsalos tal cual en criterios=\"...\")")


def cmd_esqueleto(args) -> None:
    carpeta = carpeta_tarea(args.tarea)
    tarea = ficha.leer_tarea(carpeta)
    criterios = rub.leer(tarea.ruta)
    if not criterios:
        sys.exit("TAREA.md no tiene rúbrica: sin ella no hay esqueleto que generar.")
    script = carpeta / "generar_documento.py"
    if not script.exists():
        sys.exit("No existe generar_documento.py en la tarea.")
    if "| ID |" not in tarea.ruta.read_text(encoding="utf-8"):
        rub.escribir(tarea.ruta, criterios)  # añade la columna ID a tablas antiguas
    try:
        esq.aplicar(script, criterios, args.palabras or tarea.extension, forzar=args.forzar)
    except (ValueError, FileExistsError) as e:
        sys.exit(str(e))
    total = args.palabras or tarea.extension or esq.PALABRAS_POR_DEFECTO
    print(f"Esqueleto escrito en {ruta_relativa(script)}: {len(criterios)} criterios, "
          f"~{total} palabras en total.")
    print("  Cada sección lleva un comentario con su criterio, peso y extensión orientativa.")


# --------------------------------------------------------------------------
# comprobar, generar, pdf
# --------------------------------------------------------------------------
def cmd_comprobar(args) -> None:
    carpeta = carpeta_tarea(args.tarea)
    inf = comp.comprobar(carpeta, args.docx)
    if args.actualizar and inf.coberturas:
        comp.actualizar_tarea(carpeta, inf)
    comp.imprimir(inf, carpeta)
    if args.actualizar and inf.coberturas:
        print("  TAREA.md: columna «Dónde se cumple» actualizada.")
    sys.exit(0 if inf.ok else 1)


def cmd_generar(args) -> None:
    carpeta = carpeta_tarea(args.tarea)
    script = carpeta / "generar_documento.py"
    if not script.exists():
        sys.exit(f"No existe {ruta_relativa(script)}")
    r = subprocess.run([python_del_repo(), str(script)], cwd=RAIZ)
    if r.returncode != 0:
        sys.exit(f"generar_documento.py terminó con error ({r.returncode}).")
    print()
    inf = comp.comprobar(carpeta)
    if inf.coberturas:
        comp.actualizar_tarea(carpeta, inf)
    comp.imprimir(inf, carpeta)
    fallo_pdf = False
    if not args.sin_pdf and inf.docx:
        print()
        fallo_pdf = convertir_pdf([inf.docx]) > 0
    sys.exit(0 if inf.ok and not fallo_pdf else 1)


def _limitar_escritura() -> None:
    import resource
    resource.setrlimit(resource.RLIMIT_FSIZE, (LO_LIMITE_BYTES, LO_LIMITE_BYTES))


def convertir_pdf(documentos: list) -> int:
    """Convierte cada .docx a .pdf junto a él. Devuelve el número de fallos."""
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        print("LibreOffice no está instalado: instálalo o exporta el PDF a mano desde Word.")
        return len(documentos)
    LO_TMP.mkdir(parents=True, exist_ok=True)
    LO_PERFIL.mkdir(parents=True, exist_ok=True)
    entorno = dict(os.environ, TMPDIR=str(LO_TMP))
    fallos = 0
    for docx in documentos:
        comando = [soffice, f"-env:UserInstallation={LO_PERFIL.as_uri()}", "--headless",
                   "--convert-to", "pdf", "--outdir", str(docx.parent), str(docx)]
        # Proceso en su propio grupo: si se cuelga se mata solo ese grupo, no
        # los LibreOffice que tengas abiertos.
        proc = subprocess.Popen(comando, env=entorno, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, start_new_session=True,
                                preexec_fn=_limitar_escritura if os.name == "posix" else None)
        try:
            salida, error = proc.communicate(timeout=LO_TIMEOUT)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.communicate()
            print(f"Error: {docx.name} tardó más de {LO_TIMEOUT} s; el .docx probablemente está mal "
                  "formado (p. ej. dos tablas seguidas sin párrafo entre medias).")
            fallos += 1
            continue
        pdf = docx.with_suffix(".pdf")
        if proc.returncode == 0 and pdf.exists() and pdf.stat().st_mtime >= docx.stat().st_mtime:
            print(f"PDF generado: {ruta_relativa(pdf)}")
        else:
            print(f"Error al convertir {docx.name}:\n{(error or salida).strip()}")
            fallos += 1
    return fallos


def cmd_pdf(args) -> None:
    objetivo = Path(args.ruta).resolve()
    if objetivo.is_dir():
        documentos = sorted(p for p in objetivo.glob("*.docx") if not p.name.startswith("~$"))
    elif objetivo.suffix.lower() == ".docx" and objetivo.exists():
        documentos = [objetivo]
    else:
        sys.exit(f"No es un .docx ni una carpeta: {args.ruta}")
    if not documentos:
        sys.exit(f"No hay archivos .docx en {args.ruta}")
    sys.exit(1 if convertir_pdf(documentos) else 0)


# --------------------------------------------------------------------------
# estado, marcar
# --------------------------------------------------------------------------
def cmd_estado(args) -> None:
    if not MATERIAS.is_dir():
        sys.exit("Todavía no hay materias (tareas.py materia <carpeta> \"Nombre\").")
    materias = [MATERIAS / args.materia] if args.materia else sorted(
        p for p in MATERIAS.iterdir() if p.is_dir())
    filas = []
    hoy = datetime.date.today()
    for m in materias:
        for carpeta in sorted(p for p in m.iterdir() if (p / "TAREA.md").exists()):
            t = ficha.leer_tarea(carpeta)
            if t.estado == "entregada" and not args.todas:
                continue
            criterios = rub.leer(t.ruta)
            if not criterios:
                cobertura = "sin rúbrica"
            elif comp.buscar_docx(carpeta) is None:
                cobertura = f"{len(criterios)} criterios, sin .docx"
            else:
                inf = comp.comprobar(carpeta)
                cubiertos = sum(1 for c in inf.coberturas if c.cubierto)
                problemas = len(inf.errores)
                cobertura = f"{cubiertos}/{len(criterios)} cubiertos"
                cobertura += f", {problemas} error{'es' if problemas != 1 else ''}" if problemas else ""
            dias = (t.fecha - hoy).days if t.fecha else None
            filas.append((t.fecha or datetime.date.max, m.name, t.base, t.estado, dias, cobertura))
    if not filas:
        print("No hay tareas pendientes." if not args.todas else "No hay tareas.")
        return
    filas.sort()
    print(f"{'Entrega':<10}  {'Días':>5}  {'Estado':<9}  {'Materia':<14}  {'Tarea':<36}  Rúbrica")
    for fecha, materia, base, estado, dias, cobertura in filas:
        f = fecha.isoformat() if fecha != datetime.date.max else "—"
        d = "—" if dias is None else ("hoy" if dias == 0 else f"{dias:+d}")
        print(f"{f:<10}  {d:>5}  {estado:<9}  {materia[:14]:<14}  {base[:36]:<36}  {cobertura}")


def cmd_marcar(args) -> None:
    carpeta = carpeta_tarea(args.tarea)
    t = ficha.leer_tarea(carpeta)
    if args.estado in ("lista", "entregada") and not args.forzar:
        inf = comp.comprobar(carpeta)
        if not inf.ok:
            comp.imprimir(inf, carpeta)
            sys.exit(f"\nLa comprobación tiene errores; corrígelos o usa --forzar para marcarla "
                     f"como {args.estado} igualmente.")
    for ruta in ficha.marcar_estado(t, args.estado):
        print(f"Actualizado: {ruta_relativa(ruta)}")


# --------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="accion", required=True)

    sub.add_parser("verificar", help="comprueba .env, Python, LibreOffice y el repo público")

    p = sub.add_parser("materia", help="crea la carpeta de una materia")
    p.add_argument("carpeta", help="nombre en minúsculas con guiones, p. ej. programacion-web-2")
    p.add_argument("nombre", help="nombre completo de la materia")

    p = sub.add_parser("tarea", help="crea la carpeta de una tarea dentro de una materia")
    p.add_argument("materia", help="carpeta de la materia, p. ej. sgbd1")
    p.add_argument("codigo", help="código del docente: A15, P2, E1...")
    p.add_argument("titulo", help="título corto de la tarea")
    p.add_argument("--tipo", choices=TIPOS, help="se deduce de la letra del código si se omite")

    p = sub.add_parser("rubrica", help="muestra la rúbrica de TAREA.md o la importa de un .docx")
    p.add_argument("tarea", help="carpeta de la tarea")
    p.add_argument("--importar", metavar="DOCX", help="rúbrica del docente en .docx")
    p.add_argument("--forzar", action="store_true", help="sustituye los criterios que ya haya")

    p = sub.add_parser("esqueleto", help="escribe en generar_documento.py una sección por criterio")
    p.add_argument("tarea", help="carpeta de la tarea")
    p.add_argument("--palabras", type=int, help="extensión total (por defecto la de TAREA.md o 1500)")
    p.add_argument("--forzar", action="store_true", help="reescribe secciones con texto (copia .bak)")

    p = sub.add_parser("generar", help="ejecuta generar_documento.py, comprueba y convierte a PDF")
    p.add_argument("tarea", help="carpeta de la tarea")
    p.add_argument("--sin-pdf", action="store_true", help="no convierte a PDF")

    p = sub.add_parser("comprobar", help="verifica el .docx contra la rúbrica")
    p.add_argument("tarea", help="carpeta de la tarea")
    p.add_argument("--docx", help="documento a comprobar (por defecto, el más reciente)")
    p.add_argument("--actualizar", action="store_true",
                   help="rellena «Dónde se cumple» en TAREA.md")

    p = sub.add_parser("pdf", help="convierte .docx a .pdf con LibreOffice")
    p.add_argument("ruta", help="un archivo .docx o una carpeta (convierte todos sus .docx)")

    p = sub.add_parser("estado", help="tareas pendientes por fecha de entrega, con su cobertura")
    p.add_argument("materia", nargs="?", help="solo esta materia")
    p.add_argument("--todas", action="store_true", help="incluye las entregadas")

    p = sub.add_parser("marcar", help="cambia el estado en TAREA.md y en el README de la materia")
    p.add_argument("tarea", help="carpeta de la tarea")
    p.add_argument("estado", choices=ESTADOS)
    p.add_argument("--forzar", action="store_true", help="marca aunque la comprobación falle")

    args = parser.parse_args()
    {
        "verificar": cmd_verificar,
        "materia": cmd_materia,
        "tarea": cmd_tarea,
        "rubrica": cmd_rubrica,
        "esqueleto": cmd_esqueleto,
        "generar": cmd_generar,
        "comprobar": cmd_comprobar,
        "pdf": cmd_pdf,
        "estado": cmd_estado,
        "marcar": cmd_marcar,
    }[args.accion](args)


if __name__ == "__main__":
    main()
