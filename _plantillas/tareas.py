#!/usr/bin/env python3
"""Herramienta del repositorio: materias, tareas, PDF y respaldo.

Uso (desde la raíz del repositorio):
    python _plantillas/tareas.py verificar
    python _plantillas/tareas.py materia <carpeta> "<Nombre de la materia>"
    python _plantillas/tareas.py tarea <materia> <codigo> "<Título>" [--tipo T]
    python _plantillas/tareas.py pdf <archivo.docx | carpeta>
    python _plantillas/tareas.py respaldo ["mensaje"]
    python _plantillas/tareas.py restaurar

Ejemplos:
    python _plantillas/tareas.py materia programacion-web-2 "Programación Web 2"
    python _plantillas/tareas.py tarea sgbd1 A15 "Procedimientos almacenados"
    python _plantillas/tareas.py pdf materias/sgbd1/A15_Procedimientos_Almacenados

Las materias se crean siempre dentro de materias/; <materia> es solo el nombre
de su carpeta (sgbd1), no la ruta.
"""
import argparse
import datetime
import importlib.util
import os
import re
import resource
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import ARCHIVO_ENV, RAIZ, ConfigError, cargar, cargar_o_salir  # noqa: E402

PLANTILLAS = RAIZ / "_plantillas"
MATERIAS = RAIZ / "materias"
TIPOS = {
    "actividad": "Actividad (A)",
    "practica": "Práctico-experimental (P)",
    "evaluacion": "Evaluación (E)",
    "otro": "Otro",
}

# Respaldo privado: un segundo repositorio git que comparte esta carpeta como
# árbol de trabajo pero ignora el .gitignore público (se añade con --force).
RESPALDO_GIT = RAIZ / ".respaldo.git"
RESPALDO_EXCLUIR = [
    ".git/**", ".respaldo.git/**", ".env",
    "**/.venv/**", "**/venv/**", "**/node_modules/**",
    "**/__pycache__/**", "**/*.pyc", "**/.playwright-mcp/**", "**/.claude/**",
    "**/.DS_Store", "**/Thumbs.db", "**/*.pdf.tmp", "**/.~lock.*#",
]

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


def nombre_materia(carpeta: Path) -> str:
    readme = carpeta / "README.md"
    if readme.exists():
        for linea in readme.read_text(encoding="utf-8").splitlines():
            if linea.startswith("# "):
                return linea[2:].strip()
    return carpeta.name


def rellenar(plantilla: Path, **valores) -> str:
    texto = plantilla.read_text(encoding="utf-8")
    for clave, valor in valores.items():
        texto = texto.replace("{" + clave + "}", valor)
    return texto


def git(*args, respaldo=False, check=True, capturar=False):
    base = ["git"]
    if respaldo:
        base += [f"--git-dir={RESPALDO_GIT}", f"--work-tree={RAIZ}"]
    return subprocess.run(
        base + list(args), cwd=RAIZ, check=check, text=True,
        capture_output=capturar,
    )


# --------------------------------------------------------------------------
# Comandos
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
        informe(True, f"respaldo remoto: {cfg['RESPALDO_REMOTO'] or 'no configurado (solo local)'}")
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
                  "requirements.txt", "_plantillas/")
    rastreados = git("ls-files", capturar=True).stdout.splitlines()
    fuera = [f for f in rastreados if not f.startswith(permitidos)]
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
        sys.exit(f"Ya existe: {destino.relative_to(RAIZ)}")

    materia_nombre = nombre_materia(carpeta_materia)
    ruta_carpeta = destino.relative_to(RAIZ).as_posix()
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
                 titulo=args.titulo, materia_nombre=materia_nombre, base=base,
                 ruta_carpeta=ruta_carpeta, ruta_script=f"{ruta_carpeta}/generar_documento.py"),
        encoding="utf-8",
    )

    readme = carpeta_materia / "README.md"
    if readme.exists():
        texto = readme.read_text(encoding="utf-8")
        if "| Carpeta | Entrega | Estado |" in texto:
            fila = f"| `{base}` | {codigo} — {args.titulo} | pendiente |\n"
            readme.write_text(texto.rstrip("\n") + "\n" + fila, encoding="utf-8")

    print(f"Tarea creada: {ruta_carpeta}/")
    print("  1. Deja el enunciado y la RÚBRICA del docente en enunciado/.")
    print("  2. Completa TAREA.md: fecha, qué se entrega, formato y notas.")
    print(f"  3. Pídele al agente de IA: \"lee AGENTS.md y haz la tarea {ruta_carpeta}\".")


def _limitar_escritura() -> None:
    resource.setrlimit(resource.RLIMIT_FSIZE, (LO_LIMITE_BYTES, LO_LIMITE_BYTES))


def cmd_pdf(args) -> None:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        sys.exit("LibreOffice no está instalado. Instálalo (p. ej. `sudo pacman -S libreoffice-fresh`) "
                 "o exporta el PDF a mano desde Word.")
    objetivo = Path(args.ruta).resolve()
    if objetivo.is_dir():
        documentos = sorted(p for p in objetivo.glob("*.docx") if not p.name.startswith("~$"))
    elif objetivo.suffix.lower() == ".docx" and objetivo.exists():
        documentos = [objetivo]
    else:
        sys.exit(f"No es un .docx ni una carpeta: {args.ruta}")
    if not documentos:
        sys.exit(f"No hay archivos .docx en {args.ruta}")

    LO_TMP.mkdir(parents=True, exist_ok=True)
    LO_PERFIL.mkdir(parents=True, exist_ok=True)
    entorno = dict(os.environ, TMPDIR=str(LO_TMP))
    fallos = 0
    for docx in documentos:
        comando = [soffice, f"-env:UserInstallation={LO_PERFIL.as_uri()}", "--headless",
                   "--convert-to", "pdf", "--outdir", str(docx.parent), str(docx)]
        try:
            r = subprocess.run(comando, env=entorno, preexec_fn=_limitar_escritura,
                               capture_output=True, text=True, timeout=LO_TIMEOUT)
            pdf = docx.with_suffix(".pdf")
            if r.returncode == 0 and pdf.exists():
                print(f"PDF generado: {pdf.relative_to(RAIZ) if pdf.is_relative_to(RAIZ) else pdf}")
                continue
            print(f"Error al convertir {docx.name}:\n{r.stderr.strip() or r.stdout.strip()}")
        except subprocess.TimeoutExpired:
            print(f"Error: {docx.name} tardó más de {LO_TIMEOUT} s; el .docx probablemente está mal "
                  "formado (p. ej. dos tablas seguidas sin párrafo entre medias).")
            subprocess.run(["pkill", "-f", "soffice"], check=False)
        fallos += 1
    sys.exit(1 if fallos else 0)


def cmd_respaldo(args) -> None:
    cfg = cargar_o_salir()
    if not RESPALDO_GIT.exists():
        git("init", "-q", "--bare", str(RESPALDO_GIT))
        git("config", "core.bare", "false", respaldo=True)
        print(f"Repositorio de respaldo creado en {RESPALDO_GIT.name}/")
    # Un clon --bare puede dejar HEAD en otra rama; el respaldo siempre va en main.
    git("symbolic-ref", "HEAD", "refs/heads/main", respaldo=True)

    # Repositorios git anidados (proyectos con su propio repo) no se copian.
    anidados = sorted(
        p.parent.relative_to(RAIZ).as_posix()
        for p in RAIZ.glob("*/**/.git")
        if ".venv" not in p.parts and "node_modules" not in p.parts
    )
    excluir = RESPALDO_EXCLUIR + [f"{a}/**" for a in anidados]
    pathspec = ["."] + [f":(exclude,glob){patron}" for patron in excluir]
    git("add", "--all", "--force", "--", *pathspec, respaldo=True)

    if git("diff", "--cached", "--quiet", respaldo=True, check=False).returncode == 0:
        print("Respaldo: no hay cambios desde el último respaldo.")
    else:
        mensaje = args.mensaje or f"Respaldo {datetime.datetime.now():%Y-%m-%d %H:%M}"
        git("commit", "-q", "-m", mensaje, respaldo=True)
        resumen = git("show", "--stat", "--format=%h %s", "HEAD", respaldo=True, capturar=True).stdout
        print("Respaldo guardado: " + resumen.splitlines()[0])
        print("  " + resumen.strip().splitlines()[-1].strip())
    if anidados:
        print("  Omitidos (tienen su propio repositorio git): " + ", ".join(anidados))

    remoto = cfg["RESPALDO_REMOTO"]
    if not remoto:
        print("  Solo local: define RESPALDO_REMOTO en .env para subirlo a un repositorio privado.")
        return
    actual = git("remote", "get-url", "origin", respaldo=True, check=False, capturar=True)
    if actual.returncode != 0:
        git("remote", "add", "origin", remoto, respaldo=True)
    elif actual.stdout.strip() != remoto:
        git("remote", "set-url", "origin", remoto, respaldo=True)
    git("push", "-q", "-u", "origin", "main", respaldo=True)
    print(f"  Subido a {remoto}")


def cmd_restaurar(_args) -> None:
    cfg = cargar_o_salir()
    remoto = cfg["RESPALDO_REMOTO"]
    if not remoto:
        sys.exit("Define RESPALDO_REMOTO en .env con la URL del repositorio privado.")
    if RESPALDO_GIT.exists():
        sys.exit(f"Ya existe {RESPALDO_GIT.name}/: las materias ya están enlazadas al respaldo.")
    git("clone", "-q", "--bare", remoto, str(RESPALDO_GIT))
    git("config", "core.bare", "false", respaldo=True)
    git("symbolic-ref", "HEAD", "refs/heads/main", respaldo=True)
    git("checkout", "main", "--", ".", respaldo=True)
    # El kit (plantillas, README...) se queda en la versión del repo público.
    git("checkout", "HEAD", "--", ".")
    print(f"Materias restauradas desde {remoto}")


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

    p = sub.add_parser("pdf", help="convierte .docx a .pdf con LibreOffice")
    p.add_argument("ruta", help="un archivo .docx o una carpeta (convierte todos sus .docx)")

    p = sub.add_parser("respaldo", help="guarda todas las materias en el repositorio privado")
    p.add_argument("mensaje", nargs="?", help="mensaje del respaldo (opcional)")

    sub.add_parser("restaurar", help="recupera las materias desde el respaldo privado (equipo nuevo)")

    args = parser.parse_args()
    {
        "verificar": cmd_verificar,
        "materia": cmd_materia,
        "tarea": cmd_tarea,
        "pdf": cmd_pdf,
        "respaldo": cmd_respaldo,
        "restaurar": cmd_restaurar,
    }[args.accion](args)


if __name__ == "__main__":
    main()
