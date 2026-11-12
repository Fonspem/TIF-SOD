"""Paso 5 y paso 7: descarga todos los documentos y compara su SHA-256 con el manifiesto.

El manifiesto (results/manifest.csv) lo escribe el script de carga, con las
columnas key, sha256 y bytes. Sale con código 1 si algún documento falta o
difiere. También informa el rendimiento de lectura (MB/s): junto con el de
escritura que informa load.py y la latencia de la sonda, es la medición base
del Paso 3.

    python verify.py                       # usa ../results/manifest.csv
    python verify.py --manifiesto otro.csv --salida ../results/verificacion_e1.csv
    python verify.py --copia ../respaldo/actas   # además guarda cada acta correcta (respaldo)

Con --copia, la misma pasada que verifica hace la copia de respaldo del bucket:
solo se guardan las actas cuyo hash coincide con el manifiesto.
"""
import argparse
import csv
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from common import BUCKET, sha256, with_failover

COPIA = None  # carpeta de la copia de respaldo (--copia); None = no copiar


def guardar(key, datos):
    destino = (COPIA / key).resolve()
    if COPIA not in destino.parents:  # una clave con ".." no puede salir de la carpeta
        raise ValueError(f"clave fuera de la carpeta de copia: {key}")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(datos)


def revisar(fila):
    try:
        datos = with_failover(lambda c: c.get_object(
            Bucket=BUCKET, Key=fila["key"])["Body"].read())
    except Exception as e:  # noqa: BLE001
        return fila["key"], "ERROR", str(e)[:80], 0
    igual = sha256(datos) == fila["sha256"]
    if igual and COPIA:
        try:
            guardar(fila["key"], datos)
        except (OSError, ValueError) as e:
            return fila["key"], "ERROR", f"copia: {e}"[:80], len(datos)
    return (fila["key"], "OK" if igual else "CORRUPTO", "",
            len(datos))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manifiesto", default="../results/manifest.csv")
    p.add_argument("--salida", help="CSV con el resultado de cada documento")
    p.add_argument("--hilos", type=int, default=8)
    p.add_argument("--copia", help="carpeta donde guardar una copia de cada acta correcta (respaldo)")
    args = p.parse_args()
    global COPIA
    if args.copia:
        COPIA = Path(args.copia).resolve()
        COPIA.mkdir(parents=True, exist_ok=True)

    with open(args.manifiesto, newline="") as f:
        manifiesto = list(csv.DictReader(f))
    inicio = time.monotonic()
    with ThreadPoolExecutor(args.hilos) as ex:
        resultados = list(ex.map(revisar, manifiesto))
    segundos = time.monotonic() - inicio
    leidos = sum(r[3] for r in resultados)
    malos = [r for r in resultados if r[1] != "OK"]
    print(f"OK: {len(resultados) - len(malos)} / {len(resultados)}  fallas: {len(malos)}")
    print(f"Lectura: {leidos / 1e6:.0f} MB en {segundos:.0f} s ({leidos / 1e6 / max(segundos, 0.001):.1f} MB/s)")
    if COPIA:
        print(f"Copia: {len(resultados) - len(malos)} actas en {COPIA}")
    for r in malos[:20]:
        print(r[:3])
    if args.salida:
        with open(args.salida, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["key", "resultado", "detalle"])
            w.writerows(r[:3] for r in resultados)
    return 1 if malos else 0


if __name__ == "__main__":
    sys.exit(main())
