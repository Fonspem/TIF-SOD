"""Cuándo dejó de responder una VM y cómo estaba la memoria justo antes.

Consulta a Prometheus (en el anfitrión) el node_exporter de la VM: muestra las caídas y
vueltas de las últimas horas y, para la última caída, los 10 minutos previos minuto a minuto.

Columnas de la tabla:
  libre     memoria disponible en la VM (MemAvailable)
  fallos/s  fallos de página mayores por segundo: lecturas de disco forzadas por falta de
            memoria; si suben mucho justo antes de la caída, la VM se quedó sin memoria
  OOM       procesos matados por falta de memoria dentro de la VM desde que arrancó
  libre EXO memoria disponible en el anfitrión

Uso (desde scripts/, en el anfitrión):  python caidas.py --vm vm3 --horas 8
"""
import argparse
import json
import time
import urllib.parse
import urllib.request

p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
p.add_argument("--vm", default="vm3")
p.add_argument("--horas", type=float, default=8)
p.add_argument("--prometheus", default="http://127.0.0.1:9090")
args = p.parse_args()

fin = time.time()
ini = fin - args.horas * 3600
VM = f'job="nodos",vm="{args.vm}"'


def serie(consulta):
    """{segundo: valor} de la consulta en el intervalo, cada 30 s."""
    q = urllib.parse.urlencode({"query": consulta, "start": ini, "end": fin, "step": 30})
    with urllib.request.urlopen(f"{args.prometheus}/api/v1/query_range?{q}", timeout=30) as r:
        res = json.load(r)["data"]["result"]
    return {round(float(t)): float(v) for t, v in res[0]["values"]} if res else {}


def hora(t):
    return time.strftime("%H:%M", time.localtime(t))


def valor(d, t, div=1):
    return f"{d[t] / div:.0f}" if t in d else "–"


up = sorted(serie(f"up{{{VM}}}").items())
caidas = [t for (_, a), (t, b) in zip(up, up[1:]) if a == 1 and b == 0]
vueltas = [t for (_, a), (t, b) in zip(up, up[1:]) if a == 0 and b == 1]
print(f"Caídas de {args.vm}:", ", ".join(map(hora, caidas[-5:])) or f"ninguna en {args.horas:g} h")
print(f"Vueltas de {args.vm}:", ", ".join(map(hora, vueltas[-5:])) or "ninguna")
if up and up[-1][1] == 0:
    print(f"Ahora: {args.vm} sigue sin responder")

if caidas:
    c = caidas[-1]
    mem = serie(f"node_memory_MemAvailable_bytes{{{VM}}}")
    fallos = serie(f"rate(node_vmstat_pgmajfault{{{VM}}}[1m])")
    oom = serie(f"node_vmstat_oom_kill{{{VM}}}")
    exo = serie('node_memory_MemAvailable_bytes{job="anfitrion"}')
    print(f"\nÚltima caída ({hora(c)}), minuto a minuto:")
    print("hora  ·    libre · fallos/s · OOM · libre EXO")
    for t in range(c - 600, c + 1, 60):
        print(f"{hora(t)} · {valor(mem, t, 2**20):>5} MB · {valor(fallos, t):>8} · "
              f"{valor(oom, t):>3} · {valor(exo, t, 2**20)} MB")
