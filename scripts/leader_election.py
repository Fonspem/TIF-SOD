"""Paso 2 / E2: mide cuánto tarda etcd en elegir un nuevo líder.

Corre en el anfitrión. En cada repetición identifica al líder, lo detiene y,
consultando por HTTP a los otros dos miembros cada 20 ms, mide:
  - t_lider_ms: hasta que un miembro informa un líder nuevo;
  - t_escritura_ms: hasta que se acepta una escritura.
Después vuelve a levantar el miembro y espera a que el clúster se estabilice.

Modos, que dan resultados muy distintos:
  kill  -> kill -9 al proceso (caída real: los seguidores esperan el tiempo de elección).
  stop  -> systemctl stop (SIGTERM: etcd transfiere el liderazgo antes de apagarse).

La orden de detener viaja por una conexión SSH persistente (ControlMaster) que se
abre antes de medir, para que la demora del envío sea de pocos milisegundos.

Ejemplo (desde scripts/, con ../ansible/ssh_config generado por Vagrant):
    python leader_election.py --modo kill --repeticiones 10 --salida ../results/e2_kill.csv
    python leader_election.py --modo stop --repeticiones 10 --salida ../results/e2_stop.csv
"""
import argparse
import base64
import csv
import statistics
import subprocess
import sys
import time

import requests

SSH = ("ssh -F {ssh_config} -o ControlMaster=auto -o ControlPath=/tmp/tif-ssh-%h "
       "-o ControlPersist=10m {host}")
DETENER = {"kill": SSH + " 'sudo pkill -9 -x etcd'", "stop": SSH + " 'sudo systemctl stop etcd'"}
INICIAR = SSH + " 'sudo systemctl start etcd'"
PRECALENTAR = SSH + " true"


def estado(endpoint, timeout=0.25):
    """(member_id, leader_id) del miembro, o None si no responde."""
    try:
        r = requests.post(f"http://{endpoint}/v3/maintenance/status", json={}, timeout=timeout).json()
        return int(r["header"]["member_id"]), int(r.get("leader", 0))
    except (requests.RequestException, KeyError, ValueError):
        return None


def escribir(endpoint, n, timeout=0.3):
    cuerpo = {"key": base64.b64encode(b"/probe").decode(), "value": base64.b64encode(str(n).encode()).decode()}
    try:
        return requests.post(f"http://{endpoint}/v3/kv/put", json=cuerpo, timeout=timeout).ok
    except requests.RequestException:
        return False


def esperar_estable(miembros, segundos=60):
    """Espera a que los 3 respondan y coincidan en un líder; devuelve (host_lider, id_lider)."""
    fin = time.time() + segundos
    while time.time() < fin:
        estados = {h: estado(ep) for h, ep in miembros.items()}
        lideres = {s[1] for s in estados.values() if s}
        if all(estados.values()) and len(lideres) == 1 and 0 not in lideres:
            lider = lideres.pop()
            host = next(h for h, s in estados.items() if s[0] == lider)
            return host, lider
        time.sleep(0.2)
    raise RuntimeError(f"el clúster no se estabilizó: {estados}")


def shell(plantilla, **valores):
    return plantilla.format(**valores)


def medir(miembros, args, n):
    host, lider_id = esperar_estable(miembros)
    vivos = {h: ep for h, ep in miembros.items() if h != host}
    subprocess.run(shell(args.precalentar, host=host, ssh_config=args.ssh_config), shell=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    t0 = time.perf_counter()
    orden = subprocess.Popen(shell(args.detener, host=host, ssh_config=args.ssh_config), shell=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    t_lider = t_escritura = None
    nuevo = None
    while time.perf_counter() - t0 < 30 and (t_lider is None or t_escritura is None):
        if t_lider is None:
            for h, ep in vivos.items():
                s = estado(ep)
                if s and s[1] not in (0, lider_id):
                    t_lider = time.perf_counter() - t0
                    nuevo = next((x for x, e in vivos.items() if (estado(e) or (0,))[0] == s[1]), "?")
                    break
        if t_lider is not None and t_escritura is None and any(escribir(ep, n) for ep in vivos.values()):
            t_escritura = time.perf_counter() - t0
        time.sleep(0.02)
    _, err = orden.communicate(timeout=60)
    if orden.returncode not in (0, 255) and err:
        print(f"  aviso: la orden de detener devolvió {orden.returncode}: {err.decode().strip()[:120]}")

    subprocess.run(shell(args.iniciar, host=host, ssh_config=args.ssh_config), shell=True, check=False)
    time.sleep(args.espera)
    fila = [n, args.modo, host, nuevo,
            round(t_lider * 1000) if t_lider is not None else "",
            round(t_escritura * 1000) if t_escritura is not None else ""]
    print(f"  corrida {n:2d}: cayó {host}, nuevo líder {nuevo}: "
          f"{fila[4]} ms hasta el líder, {fila[5]} ms hasta la primera escritura")
    return fila


def resumen(filas, columna, nombre):
    valores = [f[columna] for f in filas if f[columna] != ""]
    if valores:
        print(f"{nombre}: mediana {statistics.median(valores):.0f} ms, "
              f"mínimo {min(valores)} ms, máximo {max(valores)} ms ({len(valores)} corridas)")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--miembros", default="vm1=192.168.56.11:2379,vm2=192.168.56.12:2379,vm3=192.168.56.13:2379",
                   help="host=ip:puerto separados por comas")
    p.add_argument("--modo", choices=DETENER, default="kill")
    p.add_argument("--repeticiones", type=int, default=10)
    p.add_argument("--espera", type=float, default=10, help="segundos para que el miembro vuelva a sumarse")
    p.add_argument("--ssh-config", default="../ansible/ssh_config")
    p.add_argument("--detener", help="plantilla de shell con {host}; por defecto depende de --modo")
    p.add_argument("--iniciar", default=INICIAR)
    p.add_argument("--precalentar", default=PRECALENTAR)
    p.add_argument("--salida", default=None, help="CSV de resultados")
    args = p.parse_args()
    args.detener = args.detener or DETENER[args.modo]
    miembros = dict(m.split("=", 1) for m in args.miembros.split(","))

    print(f"Modo {args.modo}, {args.repeticiones} repeticiones")
    filas = [medir(miembros, args, n) for n in range(1, args.repeticiones + 1)]
    resumen(filas, 4, "Nuevo líder")
    resumen(filas, 5, "Primera escritura")
    if args.salida:
        with open(args.salida, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["corrida", "modo", "lider_caido", "lider_nuevo", "t_lider_ms", "t_escritura_ms"])
            w.writerows(filas)
        print(f"Resultados en {args.salida}")


if __name__ == "__main__":
    sys.exit(main())
