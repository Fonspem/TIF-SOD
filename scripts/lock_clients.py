"""Paso 4 y E5: clientes que compiten por el bloqueo de un documento.

Modos:
  concurrencia  N clientes piden el bloqueo a la vez: uno obtiene 200 y el resto 409.
  huerfano      E5. Un proceso dueño toma el bloqueo y lo renueva cada TTL/3; se lo
                mata con kill -9 (o, con --ordenado, con SIGTERM y libera el bloqueo)
                y se mide cuánto tarda otro cliente en obtenerlo.
  fencing       El dueño se "pausa" más que el TTL, otro cliente toma el bloqueo y la
                escritura del dueño viejo tiene que ser rechazada (409).

Ejemplos (con la API en el puerto 5000):
    python lock_clients.py concurrencia --clientes 2
    python lock_clients.py huerfano --repeticiones 5 --salida ../results/e5_kill.csv
    python lock_clients.py huerfano --ordenado --repeticiones 5 --salida ../results/e5_ordenado.csv
    python lock_clients.py fencing
"""
import argparse
import csv
import os
import random
import signal
import statistics
import subprocess
import sys
import threading
import time

import requests


def registrar(api, doc):
    requests.post(f"{api}/docs/{doc}", json={}, timeout=5)  # 201 o 409 si ya existía


def pedir_bloqueo(api, doc, duenio):
    return requests.post(f"{api}/docs/{doc}/lock", json={"owner": duenio}, timeout=5)


def concurrencia(args):
    registrar(args.api, args.doc)
    barrera = threading.Barrier(args.clientes)
    resultados = {}

    def cliente(i):
        barrera.wait()
        resultados[f"cliente-{i}"] = pedir_bloqueo(args.api, args.doc, f"cliente-{i}")

    hilos = [threading.Thread(target=cliente, args=(i,)) for i in range(1, args.clientes + 1)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    for nombre, r in sorted(resultados.items()):
        print(f"{nombre}: {r.status_code} {r.json()}")
    ganadores = [r for r in resultados.values() if r.status_code == 200]
    for r in ganadores:
        requests.delete(f"{args.api}/docs/{args.doc}/lock", json={"token": r.json()["token"]}, timeout=5)
    print("OK: exactamente un cliente obtuvo el bloqueo" if len(ganadores) == 1 else "ERROR: más de un dueño")


def duenio(args):
    """Proceso hijo: toma el bloqueo, avisa por stdout y lo renueva hasta que lo maten."""
    while True:
        r = pedir_bloqueo(args.api, args.doc, f"duenio-{os.getpid()}")
        if r.status_code == 200:
            break
        time.sleep(0.1)
    lock = r.json()

    def liberar(*_):
        requests.delete(f"{args.api}/docs/{args.doc}/lock", json={"token": lock["token"]}, timeout=5)
        os._exit(0)

    signal.signal(signal.SIGTERM, liberar)
    print(f"TOMADO {lock['token']} {lock['ttl']}", flush=True)
    while True:
        time.sleep(lock["ttl"] / 3)
        requests.post(f"{args.api}/docs/{args.doc}/lock/refresh", json={"lease": lock["lease"]}, timeout=5)


def huerfano(args):
    registrar(args.api, args.doc)
    senal = signal.SIGTERM if args.ordenado else signal.SIGKILL
    filas = []
    for n in range(1, args.repeticiones + 1):
        hijo = subprocess.Popen([sys.executable, __file__, "_duenio", "--api", args.api, "--doc", args.doc],
                                stdout=subprocess.PIPE, text=True)
        linea = hijo.stdout.readline().split()
        if not linea or linea[0] != "TOMADO":
            raise RuntimeError("el proceso dueño no pudo tomar el bloqueo")
        ttl = int(linea[2])
        time.sleep(random.uniform(0.5, 2.0) * ttl / 3)  # matar en un punto cualquiera del ciclo de renovación
        t0 = time.perf_counter()
        hijo.send_signal(senal)
        while True:
            r = pedir_bloqueo(args.api, args.doc, "segundo-cliente")
            if r.status_code == 200:
                break
            time.sleep(0.05)
        t = time.perf_counter() - t0
        hijo.wait()
        requests.delete(f"{args.api}/docs/{args.doc}/lock", json={"token": r.json()["token"]}, timeout=5)
        filas.append([n, "ordenado" if args.ordenado else "kill -9", ttl, round(t, 2)])
        print(f"  corrida {n}: el segundo cliente obtuvo el bloqueo a los {t:.2f} s (TTL {ttl} s)")
    tiempos = [f[3] for f in filas]
    print(f"Liberación: mediana {statistics.median(tiempos):.2f} s, mínimo {min(tiempos):.2f} s, "
          f"máximo {max(tiempos):.2f} s")
    if args.salida:
        with open(args.salida, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["corrida", "modo", "ttl_s", "t_liberacion_s"])
            w.writerows(filas)


def fencing(args):
    doc = args.doc + "-fencing-" + str(int(time.time()))
    registrar(args.api, doc)
    a = pedir_bloqueo(args.api, doc, "A").json()
    print(f"A obtuvo el bloqueo con token {a['token']} y se pausa sin renovarlo")
    while True:  # B insiste hasta que vence el lease de A
        rb = pedir_bloqueo(args.api, doc, "B")
        if rb.status_code == 200:
            break
        time.sleep(0.2)
    b = rb.json()
    print(f"B obtuvo el bloqueo con token {b['token']}")
    ra = requests.put(f"{args.api}/docs/{doc}/state", json={"estado": "firmada", "token": a["token"]}, timeout=5)
    print(f"A se despierta y quiere firmar con su token viejo: {ra.status_code} {ra.json()}")
    rb = requests.put(f"{args.api}/docs/{doc}/state", json={"estado": "firmada", "token": b["token"]}, timeout=5)
    print(f"B firma con su token: {rb.status_code} {rb.json()}")
    print("OK: el fencing token rechazó al dueño viejo" if ra.status_code == 409 and rb.status_code == 200
          else "ERROR: el fencing no funcionó")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("modo", choices=["concurrencia", "huerfano", "fencing", "_duenio"])
    p.add_argument("--api", default="http://localhost:5000")
    p.add_argument("--doc", default="acta-demo")
    p.add_argument("--clientes", type=int, default=2)
    p.add_argument("--repeticiones", type=int, default=5)
    p.add_argument("--ordenado", action="store_true", help="en huerfano: SIGTERM y liberación en vez de kill -9")
    p.add_argument("--salida")
    args = p.parse_args()
    {"concurrencia": concurrencia, "huerfano": huerfano, "fencing": fencing, "_duenio": duenio}[args.modo](args)


if __name__ == "__main__":
    main()
