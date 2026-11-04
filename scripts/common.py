"""Cliente S3 compartido por los scripts de carga y verificación.

Cada pod de MinIO expone el puerto 9000 en su propio nodo (hostPort), así que
cada URL de NODES habla con una unidad concreta. with_failover prueba los nodos
en orden hasta que uno responde, para no depender de un solo nodo cuando se
apaga una VM.

Credenciales por variables de entorno: MINIO_USER y MINIO_PASS.
"""
import hashlib
import os

import boto3
from botocore.config import Config

NODES = os.environ.get(
    "MINIO_NODES",
    "http://192.168.56.11:9000,http://192.168.56.12:9000,http://192.168.56.13:9000,http://192.168.56.14:9000",
).split(",")
BUCKET = os.environ.get("MINIO_BUCKET", "actas")


def s3(node):
    return boto3.client(
        "s3", endpoint_url=node,
        aws_access_key_id=os.environ.get("MINIO_USER", "admin"),
        aws_secret_access_key=os.environ.get("MINIO_PASS", ""),
        region_name="us-east-1",
        config=Config(retries={"max_attempts": 1}, connect_timeout=3, read_timeout=10),
    )


def with_failover(fn):
    """Ejecuta fn(cliente) contra el primer nodo que responda; si ninguno responde, relanza el último error."""
    ultimo = None
    for node in NODES:
        try:
            return fn(s3(node))
        except Exception as e:  # noqa: BLE001 (cualquier falla de red o de MinIO pasa al siguiente nodo)
            ultimo = e
    raise ultimo


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
