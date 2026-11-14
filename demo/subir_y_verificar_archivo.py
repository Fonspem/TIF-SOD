"""Sube un archivo cualquiera al repositorio, muestra lo que quedó registrado y lo baja comprobando que
llegó intacto. Sirve para la demo con un archivo real (una foto o un PDF traído en el momento).

    python subir_y_verificar_archivo.py subir foto.jpg              # a MinIO, y su SHA-256 a etcd
    python subir_y_verificar_archivo.py ver foto                    # qué guarda etcd: hash, tamaño, estado
    python subir_y_verificar_archivo.py bajar foto --salida /tmp/   # lo baja y compara el hash con el de etcd

El identificador es el nombre del archivo sin la extensión (o el que se pase con --id), con letras,
números, guiones y guiones bajos. El objeto queda en el mismo bucket que las actas, con el prefijo
demo/, así verify.py no lo cuenta. Credenciales: MINIO_USER y MINIO_PASS, como en load.py.
"""
import argparse
import re
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))   # usa el cliente S3 de scripts/common.py
import common  # noqa: E402
from common import BUCKET, NODES, sha256, with_failover  # noqa: E402


def miles(n):
    return f"{n:,}".replace(",", ".")


def nodo_usado():
    return NODES[common._preferido].split("//")[-1]


def identificador(nombre):
    ident = re.sub(r"[^A-Za-z0-9_-]+", "-", nombre).strip("-")
    if not ident:
        sys.exit(f"No pude armar un identificador con «{nombre}»: pasá --id")
    return ident


def subir(args):
    ruta = Path(args.archivo)
    datos = ruta.read_bytes()
    ident = args.id or identificador(ruta.stem)
    huella = sha256(datos)
    objeto = f"demo/{ident}{ruta.suffix}"
    inicio = time.monotonic()
    with_failover(lambda c: c.put_object(Bucket=BUCKET, Key=objeto, Body=datos, Metadata={"sha256": huella}))
    s = time.monotonic() - inicio
    print(f"Subido: {objeto} ({miles(len(datos))} bytes en {s:.1f} s, por {nodo_usado()})")
    print(f"SHA-256: {huella}")
    r = requests.post(f"{args.api}/docs/{ident}", json={"sha256": huella, "bytes": len(datos), "objeto": objeto},
                      timeout=10)
    if r.status_code == 201:
        print(f"Registrado en etcd como «{ident}», en estado borrador")
    elif r.status_code == 409:
        guardado = requests.get(f"{args.api}/docs/{ident}", timeout=10).json()
        if guardado.get("sha256") != huella:
            sys.exit(f"«{ident}» ya existe en etcd con otro contenido: usá otro --id")
        print(f"«{ident}» ya estaba registrado con el mismo hash")
    else:
        sys.exit(f"Servicio de metadatos: HTTP {r.status_code} {r.text[:200]}")
    return 0


def metadatos(api, ident):
    r = requests.get(f"{api}/docs/{ident}", timeout=10)
    if r.status_code == 404:
        sys.exit(f"«{ident}» no está registrado en etcd")
    r.raise_for_status()
    return r.json()


def ver(args):
    for k, v in metadatos(args.api, args.id).items():
        print(f"  {k}: {v}")
    return 0


def bajar(args):
    meta = metadatos(args.api, args.id)
    objeto = meta.get("objeto")
    if not objeto:
        sys.exit(f"«{args.id}» no tiene objeto asociado")
    inicio = time.monotonic()
    datos = with_failover(lambda c: c.get_object(Bucket=BUCKET, Key=objeto)["Body"].read())
    s = time.monotonic() - inicio
    huella = sha256(datos)
    salida = Path(args.salida)
    if salida.is_dir():
        salida = salida / Path(objeto).name
    salida.write_bytes(datos)
    print(f"Bajado: {objeto} → {salida} ({miles(len(datos))} bytes en {s:.1f} s, por {nodo_usado()})")
    print(f"SHA-256 recalculado: {huella}")
    print(f"SHA-256 en etcd:     {meta.get('sha256')}")
    if huella == meta.get("sha256"):
        print("OK: el archivo está intacto")
        return 0
    print("ERROR: los hashes no coinciden")
    return 1


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--api", default="http://localhost:8000", help="URL del servicio de metadatos")
    sub = p.add_subparsers(dest="accion", required=True)
    s = sub.add_parser("subir")
    s.add_argument("archivo")
    s.add_argument("--id")
    s.set_defaults(fn=subir)
    v = sub.add_parser("ver")
    v.add_argument("id")
    v.set_defaults(fn=ver)
    b = sub.add_parser("bajar")
    b.add_argument("id")
    b.add_argument("--salida", default=".")
    b.set_defaults(fn=bajar)
    args = p.parse_args()
    args.api = args.api.rstrip("/")
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
