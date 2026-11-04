"""Paso 5 y paso 7: descarga todos los documentos y compara su SHA-256 con el manifiesto.

El manifiesto (results/manifest.csv) lo escribe el script de carga, con las
columnas key, sha256 y bytes. Sale con código 1 si algún documento falta o
difiere.

    python verify.py                       # usa ../results/manifest.csv
    python verify.py --manifiesto otro.csv --salida ../results/verificacion_e1.csv
"""
import argparse
import csv
import sys
from concurrent.futures import ThreadPoolExecutor

from common import BUCKET, sha256, with_failover


def revisar(fila):
    try:
        datos = with_failover(lambda c: c.get_object(Bucket=BUCKET, Key=fila["key"])["Body"].read())
    except Exception as e:  # noqa: BLE001
        return fila["key"], "ERROR", str(e)[:80]
    return fila["key"], "OK" if sha256(datos) == fila["sha256"] else "CORRUPTO", ""


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manifiesto", default="../results/manifest.csv")
    p.add_argument("--salida", help="CSV con el resultado de cada documento")
    p.add_argument("--hilos", type=int, default=8)
    args = p.parse_args()

    with open(args.manifiesto, newline="") as f:
        manifiesto = list(csv.DictReader(f))
    with ThreadPoolExecutor(args.hilos) as ex:
        resultados = list(ex.map(revisar, manifiesto))
    malos = [r for r in resultados if r[1] != "OK"]
    print(f"OK: {len(resultados) - len(malos)} / {len(resultados)}  fallas: {len(malos)}")
    for r in malos[:20]:
        print(r)
    if args.salida:
        with open(args.salida, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["key", "resultado", "detalle"])
            w.writerows(resultados)
    return 1 if malos else 0


if __name__ == "__main__":
    sys.exit(main())
