"""Cliente S3 compartido por los scripts de carga y verificación.

Cada pod de MinIO expone el puerto 9000 en su propio nodo (hostPort), así que
cada URL de NODES habla con una unidad concreta. with_failover empieza por el
último nodo que respondió y, si falla, prueba los demás: así un nodo apagado
no le suma una espera a cada pedido.

Los clientes se crean una sola vez por nodo (crearlos es caro y no es seguro
hacerlo desde varios hilos a la vez); después se comparten, porque los clientes
de boto3 sí se pueden usar desde varios hilos.

Credenciales por variables de entorno: MINIO_USER y MINIO_PASS.
"""
import hashlib
import os
import threading

import boto3
from botocore.config import Config

NODES = os.environ.get(
    "MINIO_NODES",
    "http://192.168.56.11:9000,http://192.168.56.12:9000,http://192.168.56.13:9000,http://192.168.56.14:9000",
).split(",")
BUCKET = os.environ.get("MINIO_BUCKET", "actas")


def s3(node, config=None):
    return boto3.client(
        "s3", endpoint_url=node,
        aws_access_key_id=os.environ.get("MINIO_USER", "admin"),
        aws_secret_access_key=os.environ.get("MINIO_PASS", ""),
        region_name="us-east-1",
        config=config or Config(retries={"max_attempts": 1}, connect_timeout=3, read_timeout=10),
    )


_clientes = {}
_lock = threading.Lock()
_preferido = 0  # índice en NODES del último nodo que respondió


def cliente(node):
    """Cliente S3 de ese nodo, creado la primera vez que se pide."""
    with _lock:
        if node not in _clientes:
            _clientes[node] = s3(node)
        return _clientes[node]


def with_failover(fn):
    """Ejecuta fn(cliente) contra el primer nodo que responda; si ninguno responde, relanza el último error."""
    global _preferido
    ultimo = None
    inicio = _preferido
    for i in range(len(NODES)):
        idx = (inicio + i) % len(NODES)
        try:
            resultado = fn(cliente(NODES[idx]))
        except Exception as e:  # noqa: BLE001 (cualquier falla de red o de MinIO pasa al siguiente nodo)
            ultimo = e
            continue
        _preferido = idx
        return resultado
    raise ultimo


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
