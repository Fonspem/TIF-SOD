"""Genera el conjunto de datos de prueba: actas de examen ficticias en PDF y en texto.

El enunciado pide al menos 1.000 archivos PDF o de texto generados
sintéticamente, de tamaños variados, sin usar documentación real. Cada acta dice
en su primera línea que es ficticia. El contenido no importa para el TIF: lo que
se mide es que cada archivo llegue intacto (mismo SHA-256 al subirlo y al
bajarlo).

- Con la misma semilla salen siempre los mismos archivos, byte por byte.
- Tamaños: 60 % chicos (2 a 100 KB), 30 % medianos (100 KB a 1 MB) y 10 %
  grandes (1 a 5 MB). En total, unos 0,5 GB.
- Formatos: alrededor del 70 % PDF y el resto texto. Los grandes son siempre PDF
  con un "anexo escaneado" (una imagen de ruido que ocupa el resto del tamaño).
- Los PDF se escriben a mano (PDF 1.4 con Courier, para que las columnas queden
  alineadas), sin dependencias externas.

    python generar_actas.py                          # 1.000 actas en ../dataset/actas
    python generar_actas.py --cantidad 50 --salida /tmp/actas-prueba
"""
import argparse
import math
import random
from pathlib import Path

SEDES = ["Posadas", "Oberá", "Eldorado"]
CARRERAS = ["Ingeniería en Sistemas de Información", "Ingeniería Civil", "Ingeniería Electromecánica",
            "Arquitectura", "Licenciatura en Informática"]
MATERIAS = ["Sistemas Operativos Distribuidos", "Redes de Computadoras", "Bases de Datos I", "Bases de Datos II",
            "Análisis Matemático I", "Análisis Matemático II", "Álgebra y Geometría Analítica", "Física I",
            "Física II", "Programación I", "Programación II", "Paradigmas de Programación",
            "Arquitectura de Computadoras", "Ingeniería de Software I", "Ingeniería de Software III",
            "Probabilidad y Estadística", "Comunicaciones", "Investigación Operativa", "Simulación",
            "Seguridad Informática"]
NOMBRES = ["Ana", "Bruno", "Camila", "Diego", "Elena", "Facundo", "Gabriela", "Hernán", "Inés", "Joaquín",
           "Lucía", "Martín", "Natalia", "Octavio", "Paula", "Ramiro", "Sofía", "Tomás", "Valentina", "Walter"]
APELLIDOS = ["Acosta", "Benítez", "Cabrera", "Duarte", "Escobar", "Fernández", "Giménez", "Herrera", "Ibarra",
             "Juárez", "Kowalczuk", "Ledesma", "Martínez", "Núñez", "Ortiz", "Pereyra", "Quiroga", "Romero",
             "Sosa", "Toledo", "Urquiza", "Villalba", "Zárate"]
OBSERVACIONES = ["Se toma el examen en el aula asignada.", "Asistencia controlada con el documento de identidad.",
                 "El tribunal deja constancia de que no hubo incidentes.", "Duración del examen: tres horas.",
                 "Las notas se publican en el sistema de alumnos.", "Se habilita una consulta posterior al examen."]
AVISO = "DOCUMENTO FICTICIO GENERADO PARA PRUEBAS DEL TIF - SIN VALOR"
LINEAS_POR_PAGINA = 56


def persona(rng):
    return f"{rng.choice(APELLIDOS)}, {rng.choice(NOMBRES)}"


def lineas_del_acta(rng, numero):
    """Texto del acta: encabezado, tribunal y una fila por alumno."""
    anio = rng.choice([2025, 2026])
    lineas = [
        AVISO,
        "",
        f"ACTA DE EXAMEN N.º {numero:05d}/{anio}",
        f"Sede {rng.choice(SEDES)} · {rng.choice(CARRERAS)}",
        f"Asignatura: {rng.choice(MATERIAS)}",
        f"Fecha: {rng.randint(1, 28):02d}/{rng.randint(1, 12):02d}/{anio} · Libro {rng.randint(1, 40)} · "
        f"Folio {rng.randint(1, 300)}",
        f"Tribunal: {persona(rng)} (presidente), {persona(rng)} y {persona(rng)}",
        "",
        "N.º  Alumno                          DNI (ficticio)   Nota",
    ]
    for i in range(1, rng.randint(8, 45) + 1):
        nota = "Ausente" if rng.random() < 0.1 else str(rng.randint(1, 10))
        dni = f"{rng.randint(90, 99)}.{rng.randint(0, 999):03d}.{rng.randint(0, 999):03d}"
        lineas.append(f"{i:>3}  {persona(rng):<32}{dni:<17}{nota}")
    lineas += ["", "Observaciones:"] + ["- " + o for o in rng.sample(OBSERVACIONES, 3)]
    lineas += ["", "Firmas del tribunal: ______________   ______________   ______________"]
    return lineas


def anexo_asistencia(rng, faltan_bytes):
    """Líneas de un registro de asistencia, hasta ocupar unos faltan_bytes."""
    lineas, tam = ["", "ANEXO: REGISTRO DE ASISTENCIA A CLASES DE CONSULTA"], 0
    while tam < faltan_bytes:
        linea = (f"{rng.randint(1, 28):02d}/{rng.randint(1, 12):02d}  {persona(rng):<32}"
                 f"{'presente' if rng.random() < 0.85 else 'ausente'}")
        lineas.append(linea)
        tam += len(linea.encode()) + 1
    return lineas


# --- PDF mínimo (1.4), escrito a mano -----------------------------------------

def _texto_pdf(texto):
    b = texto.encode("cp1252", errors="replace")
    return b.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def _flujo_texto(lineas):
    partes = [b"BT /F1 9 Tf 12 TL 50 800 Td"]
    partes += [b"(" + _texto_pdf(linea) + b") Tj T*" for linea in lineas]
    partes.append(b"ET")
    return b"\n".join(partes)


def pdf(lineas, imagen=None):
    """PDF con las líneas repartidas en páginas A4 y, si hay imagen (ancho, alto, bytes grises), una página más."""
    objetos = [b"", b""]  # 1: catálogo, 2: árbol de páginas (se completan al final)

    def agregar(contenido):
        objetos.append(contenido)
        return len(objetos)

    def flujo(diccionario, datos):
        return diccionario[:-2] + b" /Length %d >>\nstream\n" % len(datos) + datos + b"\nendstream"

    fuente = agregar(b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>")
    paginas = []
    for i in range(0, max(len(lineas), 1), LINEAS_POR_PAGINA):
        contenido = agregar(flujo(b"<< >>", _flujo_texto(lineas[i:i + LINEAS_POR_PAGINA])))
        paginas.append(agregar(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
                               b"/Resources << /Font << /F1 %d 0 R >> >> /Contents %d 0 R >>" % (fuente, contenido)))
    if imagen:
        ancho, alto, datos = imagen
        escala = min(495 / ancho, 680 / alto)
        w, h = ancho * escala, alto * escala
        img = agregar(flujo(b"<< /Type /XObject /Subtype /Image /Width %d /Height %d /ColorSpace /DeviceGray "
                            b"/BitsPerComponent 8 >>" % (ancho, alto), datos))
        dibujo = (_flujo_texto(["ANEXO: COPIA ESCANEADA (imagen de prueba)"]) +
                  b"\nq %.2f 0 0 %.2f 50 %.2f cm /Im1 Do Q" % (w, h, 770 - h))
        contenido = agregar(flujo(b"<< >>", dibujo))
        paginas.append(agregar(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << "
                               b"/Font << /F1 %d 0 R >> /XObject << /Im1 %d 0 R >> >> /Contents %d 0 R >>"
                               % (fuente, img, contenido)))
    objetos[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objetos[1] = b"<< /Type /Pages /Kids [%s] /Count %d >>" % (b" ".join(b"%d 0 R" % p for p in paginas),
                                                                  len(paginas))
    salida = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    posiciones = []
    for n, obj in enumerate(objetos, 1):
        posiciones.append(len(salida))
        salida += b"%d 0 obj\n" % n + obj + b"\nendobj\n"
    xref = len(salida)
    salida += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objetos) + 1)
    salida += b"".join(b"%010d 00000 n \n" % p for p in posiciones)
    salida += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objetos) + 1, xref)
    return bytes(salida)


# --- Generación ------------------------------------------------------------------

def tamanio_objetivo(rng):
    clase = rng.random()
    if clase < 0.6:
        minimo, maximo = 2_000, 100_000
    elif clase < 0.9:
        minimo, maximo = 100_000, 1_000_000
    else:
        minimo, maximo = 1_000_000, 5_000_000
    return int(math.exp(rng.uniform(math.log(minimo), math.log(maximo)))), clase >= 0.9


def generar(numero, semilla):
    """Devuelve (nombre de archivo, contenido) del acta número `numero`."""
    rng = random.Random(semilla * 1_000_003 + numero)
    objetivo, grande = tamanio_objetivo(rng)
    lineas = lineas_del_acta(rng, numero)
    if grande or rng.random() < 2 / 3:
        datos = pdf(lineas)
        faltan = objetivo - len(datos) - 400
        if faltan > 1_000:  # el resto del tamaño lo ocupa el "anexo escaneado"
            ancho = int(math.sqrt(faltan))
            alto = faltan // ancho
            datos = pdf(lineas, (ancho, alto, rng.randbytes(ancho * alto)))
        return f"acta-{numero:04d}.pdf", datos
    texto = "\n".join(lineas) + "\n"
    faltan = objetivo - len(texto.encode())
    if faltan > 0:
        texto += "\n".join(anexo_asistencia(rng, faltan)) + "\n"
    return f"acta-{numero:04d}.txt", texto.encode()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cantidad", type=int, default=1000)
    p.add_argument("--salida", default="../dataset/actas")
    p.add_argument("--semilla", type=int, default=2026)
    args = p.parse_args()

    carpeta = Path(args.salida)
    carpeta.mkdir(parents=True, exist_ok=True)
    total, formatos = 0, {"pdf": 0, "txt": 0}
    for numero in range(1, args.cantidad + 1):
        nombre, datos = generar(numero, args.semilla)
        (carpeta / nombre).write_bytes(datos)
        total += len(datos)
        formatos[nombre.rsplit(".", 1)[1]] += 1
    print(f"{args.cantidad} actas en {carpeta}: {formatos['pdf']} PDF y {formatos['txt']} de texto, "
          f"{total / 1e6:.0f} MB en total (semilla {args.semilla}).")


if __name__ == "__main__":
    main()
