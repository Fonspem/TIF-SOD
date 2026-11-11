"""Paso 5: sube las actas a MinIO y registra el SHA-256 de cada una.

Para cada archivo de --carpeta:
1. calcula su SHA-256 (la "huella" del contenido: cambia por completo si cambia un solo bit);
2. lo sube al bucket (MINIO_BUCKET, por defecto actas) con el hash como metadato (x-amz-meta-sha256);
3. lo da de alta en el servicio de metadatos, en estado borrador, con el hash, el tamaño y el
   nombre del objeto (salvo con --sin-api).

Escribe el manifiesto (key, sha256, bytes) que después usa verify.py en el Paso 7. Se puede volver a
correr: lo que ya está en el servicio de metadatos se saltea, y si su hash no coincide se informa
como error.

    python load.py                                  # ../dataset/actas → MinIO; manifiesto en ../results/manifest.csv
    python load.py --sin-api --carpeta /tmp/actas
"""
import argparse
import csv
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

from common import BUCKET, sha256, with_failover

_local = threading.local()


def sesion():
    """Una sesión HTTP por hilo, para reusar conexiones con el servicio de metadatos."""
    if not hasattr(_local, "sesion"):
        _local.sesion = requests.Session()
    return _local.sesion


def asegurar_bucket():
    from botocore.exceptions import ClientError

    def op(c):
        try:
            c.head_bucket(Bucket=BUCKET)
        except ClientError as e:
            if e.response["Error"]["Code"] not in ("404", "NoSuchBucket"):
                raise
            c.create_bucket(Bucket=BUCKET)
    with_failover(op)


def registrar(api, doc, huella, tam, objeto):
    r = sesion().post(f"{api}/docs/{doc}", json={"sha256": huella, "bytes": tam, "objeto": objeto}, timeout=10)
    if r.status_code == 201:
        return "alta"
    if r.status_code == 409:  # ya estaba: se acepta solo si es el mismo contenido
        guardado = sesion().get(f"{api}/docs/{doc}", timeout=10).json().get("sha256")
        if guardado == huella:
            return "ya estaba"
        raise RuntimeError(f"el servicio de metadatos tiene otro hash para {doc}")
    raise RuntimeError(f"servicio de metadatos: HTTP {r.status_code}")


def subir(ruta, api):
    datos = ruta.read_bytes()
    huella = sha256(datos)
    with_failover(lambda c: c.put_object(Bucket=BUCKET, Key=ruta.name, Body=datos, Metadata={"sha256": huella}))
    estado = registrar(api, ruta.stem, huella, len(datos), ruta.name) if api else "-"
    return ruta.name, huella, len(datos), estado


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--carpeta", default="../dataset/actas")
    p.add_argument("--manifiesto", default="../results/manifest.csv")
    p.add_argument("--api", default="http://localhost:8000", help="URL del servicio de metadatos")
    p.add_argument("--sin-api", action="store_true", help="no registrar las actas en el servicio de metadatos")
    p.add_argument("--hilos", type=int, default=4)
    args = p.parse_args()
    api = None if args.sin_api else args.api.rstrip("/")

    archivos = sorted(r for r in Path(args.carpeta).iterdir() if r.is_file())
    if not archivos:
        sys.exit(f"No hay archivos en {args.carpeta}: primero corré generar_actas.py")
    asegurar_bucket()

    hechos, fallas, inicio = [], [], time.monotonic()

    def tarea(ruta):
        try:
            return subir(ruta, api), None
        except Exception as e:  # noqa: BLE001 (se informa y se sigue con el resto)
            return None, (ruta.name, str(e)[:120])

    with ThreadPoolExecutor(args.hilos) as ex:
        for n, (ok, falla) in enumerate(ex.map(tarea, archivos), 1):
            if ok:
                hechos.append(ok)
            else:
                fallas.append(falla)
            if n % 100 == 0 or n == len(archivos):
                print(f"  {n}/{len(archivos)} procesadas, {len(fallas)} con error", flush=True)

    Path(args.manifiesto).parent.mkdir(parents=True, exist_ok=True)
    with open(args.manifiesto, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["key", "sha256", "bytes"])
        w.writerows(sorted((nombre, huella, tam) for nombre, huella, tam, _ in hechos))

    segundos = time.monotonic() - inicio
    total = sum(tam for _, _, tam, _ in hechos)
    estados = {}
    for *_, estado in hechos:
        estados[estado] = estados.get(estado, 0) + 1
    print(f"Subidas: {len(hechos)} de {len(archivos)} ({total / 1e6:.0f} MB en {segundos:.0f} s, "
          f"{total / 1e6 / max(segundos, 0.001):.1f} MB/s). Manifiesto: {args.manifiesto}")
    if api:
        print("Servicio de metadatos: " + ", ".join(f"{k}: {v}" for k, v in sorted(estados.items())))
    for nombre, error in fallas[:20]:
        print(f"  ERROR {nombre}: {error}")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
