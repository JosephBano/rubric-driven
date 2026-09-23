# istpet-publico

## Propósito

Repositorio público de tareas, actividades y trabajos académicos correspondientes a la carrera de Desarrollo de Software. Sirve como respaldo y entrega ordenada de lo desarrollado en cada materia a lo largo del periodo académico.

## Datos del estudiante

- **Nombre:** Joseph Andrés Baño Naranjo
- **Institución:** Instituto Tecnológico Mayor Pedro Traversari
- **Carrera:** Desarrollo de Software

## Estructura del repositorio

Cada materia tiene su propia carpeta y, dentro de ella, una carpeta por tarea. Las carpetas de las materias existen solo en local (están en `.gitignore`); el repositorio remoto publica únicamente las plantillas y esta documentación.

### Crear una materia o tarea nueva

```bash
python _plantillas/nuevo.py materia <carpeta> "<Nombre de la materia>"
python _plantillas/nuevo.py tarea <materia> <codigo> "<Título>"
```

Cada tarea tiene `TAREA.md` (ficha a completar), `enunciado/` (material del docente) y `capturas/`. Detalles en [`_plantillas/PLANTILLA_README.md`](_plantillas/PLANTILLA_README.md).

### Requisitos del sistema

- **Python 3** con `python-docx` y `Pillow`: generan los `.docx` (se puede reutilizar el entorno `arquitectura-computacional/.venv`).
- **LibreOffice** (recomendado): convierte los `.docx` a `.pdf` y permite revisar el resultado. Sin LibreOffice los `.docx` se generan igual, pero el `.pdf` hay que exportarlo a mano (por ejemplo, desde Word).

```bash
soffice --headless --convert-to pdf --outdir . Documento.docx
```

## Formato de los documentos y actividades

Salvo que se indique lo contrario, los documentos entregables (informes, tareas, trabajos escritos) siguen este estilo por defecto:

- **Normas APA 7.ª edición.**
- **Monocromático:** texto e imágenes en blanco y negro, sin colores decorativos.
- **Portada sencilla**, sin tablas ni logos: título, nombre del estudiante, institución, carrera, materia y fecha.
- Tipografía **Times New Roman 12 pt**, interlineado doble, márgenes de 1 pulgada.
- Figuras en formato APA (rótulo, descripción en cursiva, imagen, nota explicativa) cuando el trabajo requiere evidencia visual.
- Redacción técnica, clara y directa, sin relleno.
- Toda evidencia (capturas de pantalla, resultados de ejecución) debe ser real y verificada antes de incluirse en el documento; nunca simulada o inventada.

Existe una plantilla reutilizable en Python (`python-docx`) que ya implementa este estilo: [`_plantillas/apa_docx.py`](_plantillas/apa_docx.py). Ver [`_plantillas/PLANTILLA_README.md`](_plantillas/PLANTILLA_README.md) para el modo de uso. Al generar un nuevo documento con este formato, usar esta plantilla en vez de reescribir el estilo desde cero.

### Excepción: actividades prácticas/experimentales

Para actividades **prácticas o experimentales** (instalación de software, laboratorios, ejercicios de ejecución en un entorno real, etc.), **no se asume este formato por defecto**. El formato de entrega para este tipo de actividad debe consultarse conmigo antes de generarlo.

## Nota

Este repositorio es de carácter **público**, por lo que no debe contener información sensible (contraseñas, datos personales de terceros, capturas con información privada, etc.).
