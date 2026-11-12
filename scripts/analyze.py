"""Tablas y figuras para el informe a partir de los CSV de results/.

Subcomandos:
  sonda     CSV de probe.py (E1 a E4). Disponibilidad, latencia p50/p95 y cortes
            por tramo (antes de la falla, durante, después) y la respuesta a cada
            evento: cuánto tardó en aparecer el primer error y cuánto en recuperarse.
  eleccion  CSV de leader_election.py (Paso 2 y E2).
  huerfano  CSV de lock_clients.py huerfano (E5).

Ejemplos (desde scripts/):
  python analyze.py sonda ../results/e1_sonda_s3.csv --eventos ../results/e1_eventos.csv \\
      --figura ../results/figuras/e1.png
  python analyze.py sonda ../results/e3_etcd_vm1.csv ../results/e3_etcd_vm3.csv \\
      --eventos ../results/e3_eventos.csv --figura ../results/figuras/e3_etcd.png
  python analyze.py sonda ../results/e2_sonda_meta_kill.csv --eventos ../results/e2_eventos.csv \\
      --por-accion --hasta 12:00      (deja afuera lo que la sonda anotó después de las 12)
  python analyze.py eleccion ../results/e2_kill.csv ../results/e2_stop.csv --figura ../results/figuras/e2.png
  python analyze.py huerfano ../results/e5_kill.csv ../results/e5_ordenado.csv --figura ../results/figuras/e5.png

Las tablas salen en Markdown y con coma decimal, listas para pasar al informe;
cada figura tiene su tabla. Las figuras necesitan matplotlib.
"""
import argparse
import csv
import os
import statistics
import sys
import time
from pathlib import Path

from medidas import cortes, percentil

OPERACIONES = ("lectura", "escritura")
INICIO_DE_FALLA = {"apagar", "aislar", "aplicar", "detener"}
FIN_DE_FALLA = {"encender", "revertir", "iniciar"}

# Colores (paleta de referencia validada; ver docs de dataviz): serie en azul,
# pedidos fallidos en el rojo de estado "crítico", siempre con forma de cruz.
SUPERFICIE = "#ffffff"
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
TENUE = "#898781"
GRILLA = "#e1e0d9"
EJE = "#c3c2b7"
VENTANA = "#ecebe6"
SERIE = "#2a78d6"
CRITICO = "#d03b3b"


# --- Formato con coma decimal y punto de miles, como en el informe -----------

def num(x, decimales=0):
    if x is None:
        return "–"
    texto = f"{x:,.{decimales}f}"
    return texto.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def porcentaje(parte, total):
    return f"{num(100 * parte / total, 1)} %" if total else "–"


def tabla(encabezado, filas):
    lineas = ["| " + " | ".join(encabezado) + " |", "|" + "---|" * len(encabezado)]
    lineas += ["| " + " | ".join(str(c) for c in fila) + " |" for fila in filas]
    return "\n".join(lineas)


# --- Lectura de datos ----------------------------------------------------------

def leer_sonda(ruta):
    with open(ruta, newline="") as f:
        filas = [dict(fila, t=float(fila["t"]), ok=fila["ok"] == "1", ms=float(fila["ms"]))
                 for fila in csv.DictReader(f)]
    return sorted(filas, key=lambda fila: fila["t"])


def leer_eventos(ruta):
    """Líneas 'momento,acción[,host]' como las que escriben chaos/*.sh y leader_election.py."""
    eventos = []
    with open(ruta) as f:
        for linea in f:
            partes = [p.strip() for p in linea.strip().split(",")]
            try:
                t = float(partes[0])
            except (ValueError, IndexError):
                continue  # encabezado o línea vacía
            accion = partes[1] if len(partes) > 1 else "evento"
            eventos.append((t, accion, " ".join(partes[2:])))
    return sorted(eventos)


def ventanas_de_falla(eventos, fin):
    """Pares (inicio, fin) entre una acción que inyecta la falla y la que la revierte."""
    abiertas, ventanas = {}, []
    for t, accion, host in eventos:
        if accion in INICIO_DE_FALLA:
            abiertas.setdefault(host, t)
        elif accion in FIN_DE_FALLA and host in abiertas:
            ventanas.append((abiertas.pop(host), t))
    ventanas += [(t, fin) for t in abiertas.values()]
    return sorted(ventanas)


def nombre_de_serie(ruta, filas):
    etiquetas = {f["etiqueta"] for f in filas}
    return etiquetas.pop() if len(etiquetas) == 1 else Path(ruta).stem


# --- Sonda -------------------------------------------------------------------------

def medir(pedidos, serie):
    """Indicadores de un grupo de pedidos de un mismo tipo.

    Los cortes se calculan sobre la serie completa (serie, ordenada por t) y se
    cuentan los que empiezan dentro del grupo, con su duración real aunque la
    recuperación caiga en el tramo siguiente.
    """
    ok = [p["ms"] for p in pedidos if p["ok"]]
    inicios, fin_serie = {p["t"] for p in pedidos}, serie[-1]["t"]
    duraciones = [(fin if fin is not None else fin_serie) - inicio
                  for inicio, fin, _ in cortes([(p["t"], p["ok"]) for p in serie]) if inicio in inicios]
    return {"n": len(pedidos), "ok": len(ok), "p50": percentil(ok, 50), "p95": percentil(ok, 95),
            "max": max(ok) if ok else None, "corte": max(duraciones, default=0.0)}


def tramos(pedidos, eventos, por_accion):
    """Agrupa los pedidos por el último evento anterior a cada uno ('antes' si no hubo)."""
    grupos = {}
    for p in pedidos:
        previo = [e for e in eventos if e[0] <= p["t"]]
        if previo:
            _, accion, host = previo[-1]
            nombre = accion if por_accion or not host else f"{accion} {host}"
        else:
            nombre = "antes"
        grupos.setdefault(nombre, []).append(p)
    return grupos


def respuesta_a_eventos(pedidos, eventos):
    """Para cada evento: primer error desde el evento y recuperación (primer éxito tras la última falla del tramo)."""
    filas = []
    for i, (t, accion, host) in enumerate(eventos):
        hasta = eventos[i + 1][0] if i + 1 < len(eventos) else float("inf")
        tramo = [p for p in pedidos if t <= p["t"] < hasta]
        fallas = [p for p in tramo if not p["ok"]]
        maxima = num(max(p["ms"] for p in tramo)) if tramo else "–"
        if not fallas:
            filas.append((f"{accion} {host}".strip(), "sin fallas", "–", 0, maxima))
            continue
        ultima = fallas[-1]["t"]
        exito = next((p["t"] for p in pedidos if p["t"] > ultima and p["ok"]), None)
        recuperacion = num(exito - t, 1) if exito is not None else "no se recuperó"
        filas.append((f"{accion} {host}".strip(), num(fallas[0]["t"] - t, 1), recuperacion, len(fallas), maxima))
    return filas


def hora_del_dia(hhmm, referencia):
    """Epoch de la hora HH:MM[:SS] (hora local) del mismo día que el epoch de referencia."""
    dia = time.localtime(referencia)
    partes = [int(x) for x in hhmm.split(":")] + [0]
    return time.mktime((dia.tm_year, dia.tm_mon, dia.tm_mday, partes[0], partes[1], partes[2], 0, 0, -1))


def cmd_sonda(args):
    series = {}
    for ruta in args.csv:
        filas = leer_sonda(ruta)
        if filas and (args.desde or args.hasta):
            # Recorte por hora: por ejemplo, para dejar afuera lo que anotó una corrida abortada
            desde = hora_del_dia(args.desde, filas[0]["t"]) if args.desde else float("-inf")
            hasta = hora_del_dia(args.hasta, filas[0]["t"]) if args.hasta else float("inf")
            filas = [f for f in filas if desde <= f["t"] <= hasta]
        if not filas:
            sys.exit(f"{ruta} no tiene pedidos")
        series[nombre_de_serie(ruta, filas)] = filas
    eventos = leer_eventos(args.eventos) if args.eventos else []
    # Sólo los eventos ocurridos mientras corría la sonda: el mismo archivo de eventos
    # puede acumular varias corridas (por ejemplo, E2 en modo kill y en modo stop).
    inicio = min(f["t"] for filas in series.values() for f in filas)
    fin = max(f["t"] for filas in series.values() for f in filas)
    eventos = [e for e in eventos if inicio - 1 <= e[0] <= fin + 1]

    resumen = []
    for nombre, filas in series.items():
        for op in OPERACIONES:
            pedidos = [f for f in filas if f["op"] == op]
            if not pedidos:
                continue
            grupos = tramos(pedidos, eventos, args.por_accion) if eventos else {}
            for tramo, lista in list(grupos.items()) + [("total", pedidos)]:
                m = medir(lista, pedidos)
                resumen.append([nombre, op, tramo, m["n"], porcentaje(m["ok"], m["n"]), num(m["p50"]),
                                num(m["p95"]), num(m["corte"], 1)])
    print("Disponibilidad y latencia por tramo (latencias de los pedidos exitosos):\n")
    print(tabla(["Serie", "Operación", "Tramo", "Pedidos", "Disponibilidad", "p50 (ms)", "p95 (ms)",
                 "Corte más largo (s)"], resumen))

    if eventos:
        filas_eventos = []
        for nombre, filas in series.items():
            for op in OPERACIONES:
                pedidos = [f for f in filas if f["op"] == op]
                for fila in respuesta_a_eventos(pedidos, eventos) if pedidos else []:
                    filas_eventos.append([nombre, op, *fila])
        print("\nRespuesta a cada evento (segundos desde el evento hasta el siguiente):\n")
        print(tabla(["Serie", "Operación", "Evento", "Primer error (s)", "Recuperación (s)", "Pedidos fallidos",
                     "Latencia máx. (ms)"], filas_eventos))
    if args.figura:
        figura_sonda(series, eventos, args)


# --- Elección de líder y bloqueo huérfano ------------------------------------

def leer_por_modo(rutas):
    por_modo = {}
    for ruta in rutas:
        with open(ruta, newline="") as f:
            for fila in csv.DictReader(f):
                por_modo.setdefault(fila["modo"], []).append(fila)
    return por_modo


def valores(filas, columna):
    return [float(f[columna]) for f in filas if f.get(columna) not in (None, "")]


def rango(v, decimales=0):
    return f"{num(min(v), decimales)}–{num(max(v), decimales)}" if v else "–"


def cmd_eleccion(args):
    por_modo = leer_por_modo(args.csv)
    filas = []
    for modo, datos in por_modo.items():
        lider, escritura = valores(datos, "t_lider_ms"), valores(datos, "t_escritura_ms")
        filas.append([modo, len(datos), num(statistics.median(lider)) if lider else "–", rango(lider),
                      num(statistics.median(escritura)) if escritura else "–", rango(escritura),
                      len(datos) - len(lider)])
    print("Tiempo hasta un nuevo líder y hasta la primera escritura aceptada:\n")
    print(tabla(["Modo", "Corridas", "Nuevo líder: mediana (ms)", "Mín–máx (ms)",
                 "Primera escritura: mediana (ms)", "Mín–máx (ms)", "Sin líder a los 30 s"], filas))
    if args.figura:
        figura_por_corrida(por_modo, "t_lider_ms", "ms", "Tiempo hasta el nuevo líder (ms)",
                           {"kill": "kill -9", "stop": "systemctl stop"},
                           None, args)


def cmd_huerfano(args):
    por_modo = leer_por_modo(args.csv)
    filas = []
    for modo, datos in por_modo.items():
        tiempos, ttl = valores(datos, "t_liberacion_s"), valores(datos, "ttl_s")
        filas.append([modo, len(datos), num(statistics.median(ttl)) if ttl else "–",
                      num(statistics.median(tiempos), 2) if tiempos else "–", rango(tiempos, 2)])
    print("Tiempo hasta que otro cliente obtiene el bloqueo:\n")
    print(tabla(["Modo", "Corridas", "TTL (s)", "Liberación: mediana (s)", "Mín–máx (s)"], filas))
    if args.figura:
        ttl = {modo: statistics.median(valores(d, "ttl_s")) for modo, d in por_modo.items() if valores(d, "ttl_s")}
        figura_por_corrida(por_modo, "t_liberacion_s", "s", "Tiempo hasta la liberación (s)",
                           {"kill -9": "kill -9", "ordenado": "SIGTERM (liberación ordenada)"},
                           ttl, args)


# --- Figuras -----------------------------------------------------------------------

def preparar_matplotlib():
    try:
        import matplotlib
    except ImportError:
        sys.exit("Las figuras necesitan matplotlib: pip install matplotlib")
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.family": "sans-serif", "font.size": 8, "axes.titlesize": 8.5, "axes.labelsize": 8,
        "axes.edgecolor": EJE, "axes.linewidth": 0.8, "axes.labelcolor": TINTA_2, "axes.titlecolor": TINTA,
        "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "axes.grid.axis": "y",
        "grid.color": GRILLA, "grid.linewidth": 0.6, "grid.linestyle": "-", "xtick.color": TENUE,
        "ytick.color": TENUE, "xtick.labelcolor": TINTA_2, "ytick.labelcolor": TINTA_2,
        "xtick.major.size": 0, "ytick.major.size": 0, "ytick.minor.size": 0, "figure.facecolor": SUPERFICIE,
        "axes.facecolor": SUPERFICIE, "savefig.facecolor": SUPERFICIE, "legend.frameon": False,
    })
    return plt


def guardar(fig, ruta):
    os.makedirs(os.path.dirname(os.path.abspath(ruta)), exist_ok=True)
    fig.savefig(ruta, dpi=200, bbox_inches="tight")
    print(f"\nFigura: {ruta}")


def formato_ms(valor, _pos=None):
    return num(valor) if valor >= 1 else num(valor, 1)


def figura_sonda(series, eventos, args):
    plt = preparar_matplotlib()
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter

    ops = [op for op in OPERACIONES if any(f["op"] == op for filas in series.values() for f in filas)]
    todos = [f for filas in series.values() for f in filas]
    t0 = eventos[0][0] if eventos else todos[0]["t"]
    fin = max(f["t"] for f in todos)
    ventanas = ventanas_de_falla(eventos, fin)
    # Nombres sólo donde empieza cada falla (la ventana sombreada marca hasta dónde dura), y
    # ninguno si son tantos que se pisarían (E2 repite la caída diez veces).
    etiquetas, ultimo = [], None
    arranques = [e for e in eventos if e[1] not in FIN_DE_FALLA]
    if len(arranques) <= 6:
        for t, accion, host in arranques:
            if ultimo is None or (t - ultimo) > 0.12 * (fin - todos[0]["t"]):
                etiquetas.append((t, f"{accion} {host}".strip()))
                ultimo = t
    latencias = [f["ms"] for f in todos if f["ms"] > 0]
    # Aire arriba para los nombres de los eventos, así no tapan las cruces de los pedidos fallidos.
    limites = (min(latencias) * 0.6, max(latencias) * 8)
    fig, ejes = plt.subplots(len(series), len(ops), figsize=(3.3 * len(ops), 1.9 * len(series) + 0.5),
                             sharex=True, sharey=True, squeeze=False)
    for i, (nombre, filas) in enumerate(series.items()):
        for j, op in enumerate(ops):
            ax = ejes[i][j]
            pedidos = [f for f in filas if f["op"] == op]
            for a, b in ventanas:
                ax.axvspan(a - t0, b - t0, color=VENTANA, lw=0, zorder=0)
            for t, accion, host in eventos:
                ax.axvline(t - t0, color=TENUE, lw=0.8, zorder=1)
            if i == 0:
                for t, texto in etiquetas:
                    ax.annotate(texto, (t - t0, 1), xycoords=("data", "axes fraction"), xytext=(3, -2),
                                textcoords="offset points", va="top", fontsize=7, color=TINTA_2)
            # Latencia de los pedidos exitosos; la línea se corta donde hubo fallas.
            ax.plot([p["t"] - t0 for p in pedidos], [p["ms"] if p["ok"] else float("nan") for p in pedidos],
                    color=SERIE, lw=1.4, solid_joinstyle="round", solid_capstyle="round", zorder=2)
            fallas = [p for p in pedidos if not p["ok"]]
            ax.scatter([p["t"] - t0 for p in fallas], [p["ms"] for p in fallas], marker="x", s=30,
                       color=CRITICO, linewidths=1.3, zorder=3)
            ax.set_yscale("log")
            ax.set_ylim(*limites)
            ax.yaxis.set_major_locator(LogLocator(base=10))
            ax.yaxis.set_major_formatter(FuncFormatter(formato_ms))
            ax.yaxis.set_minor_formatter(NullFormatter())
            ax.set_title(f"{nombre} · {op}s", loc="left")
            if j == 0:
                ax.set_ylabel("Latencia (ms, log)")
            if i == len(series) - 1:
                ax.set_xlabel("Segundos desde el primer evento" if eventos else "Segundos desde el inicio")
    leyenda = [Line2D([], [], color=SERIE, lw=1.4, label="Pedido exitoso (latencia)")]
    if any(not f["ok"] for f in todos):
        leyenda.append(Line2D([], [], color=CRITICO, marker="x", lw=0, markersize=6, markeredgewidth=1.3,
                              label="Pedido fallido (tiempo hasta el error)"))
    if ventanas:
        leyenda.append(Patch(color=VENTANA, label="Falla inyectada"))
    fig.legend(handles=leyenda, loc="upper left", ncol=len(leyenda), bbox_to_anchor=(0, 1.0), fontsize=7.5,
               handlelength=1.6, columnspacing=1.4)
    if args.titulo:
        fig.suptitle(args.titulo, x=0, ha="left", y=1.06, fontsize=9.5, color=TINTA)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    guardar(fig, args.figura)


def figura_por_corrida(por_modo, columna, unidad, etiqueta_y, titulos, referencia, args):
    """Un panel por modo (escalas muy distintas: nunca dos ejes y), un punto por corrida y la mediana."""
    plt = preparar_matplotlib()
    from matplotlib.lines import Line2D
    fig, ejes = plt.subplots(1, len(por_modo), figsize=(3.3 * len(por_modo), 2.5), squeeze=False)
    decimales = 0 if unidad == "ms" else 2
    for ax, (modo, datos) in zip(ejes[0], por_modo.items()):
        puntos = [(int(f["corrida"]), float(f[columna])) for f in datos if f.get(columna) not in (None, "")]
        if not puntos:
            continue
        xs, ys = zip(*puntos)
        tope = max(ys) * 1.3
        if referencia and modo in referencia:
            tope = max(tope, referencia[modo] * 1.15)
            ax.axhline(referencia[modo], color=TENUE, lw=1.0, ls=(0, (4, 3)), zorder=1)  # umbral: punteada
        mediana = statistics.median(ys)
        ax.axhline(mediana, color=TINTA_2, lw=0.8, zorder=1)
        ax.scatter(xs, ys, s=34, color=SERIE, edgecolors=SUPERFICIE, linewidths=1.5, zorder=3)
        ax.set_ylim(0, tope)
        ax.set_xticks(xs)
        ax.set_xlabel("Corrida")
        ax.set_title(f"{titulos.get(modo, modo)} · mediana {num(mediana, decimales)} {unidad}", loc="left")
        ax.yaxis.set_major_formatter(lambda v, _pos: num(v, 0 if float(v).is_integer() else 1))
    ejes[0][0].set_ylabel(etiqueta_y)
    leyenda = [Line2D([], [], color=SERIE, marker="o", lw=0, markersize=5.5, label="Corrida"),
               Line2D([], [], color=TINTA_2, lw=0.8, label="Mediana")]
    if referencia:
        leyenda.append(Line2D([], [], color=TENUE, lw=1.0, ls=(0, (4, 3)), label="TTL del lease"))
    fig.legend(handles=leyenda, loc="upper left", ncol=len(leyenda), bbox_to_anchor=(0, 1.0), fontsize=7.5,
               handlelength=1.6, columnspacing=1.4)
    if args.titulo:
        fig.suptitle(args.titulo, x=0, ha="left", y=1.06, fontsize=9.5, color=TINTA)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    guardar(fig, args.figura)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for nombre, ayuda in (("sonda", "CSV de probe.py"), ("eleccion", "CSV de leader_election.py"),
                          ("huerfano", "CSV de lock_clients.py huerfano")):
        s = sub.add_parser(nombre, help=ayuda)
        s.add_argument("csv", nargs="+")
        s.add_argument("--figura", help="PNG de salida (por ejemplo ../results/figuras/e1.png)")
        s.add_argument("--titulo", help="título dentro de la figura (el informe ya lleva su leyenda APA)")
        if nombre == "sonda":
            s.add_argument("--eventos", help="CSV de eventos de chaos/ o de leader_election.py")
            s.add_argument("--por-accion", action="store_true",
                           help="agrupar los tramos por acción, sin el host (útil en E2, donde cae un líder distinto cada vez)")
            s.add_argument("--desde", metavar="HH:MM", help="usar sólo los pedidos desde esa hora local del día de la sonda")
            s.add_argument("--hasta", metavar="HH:MM", help="usar sólo los pedidos hasta esa hora local del día de la sonda")
    args = p.parse_args()
    {"sonda": cmd_sonda, "eleccion": cmd_eleccion, "huerfano": cmd_huerfano}[args.cmd](args)


if __name__ == "__main__":
    main()
