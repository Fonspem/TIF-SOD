# scripts/: datos de prueba, mediciones, análisis y operación

Se corren desde esta carpeta, en el anfitrión, con el entorno de Python del repositorio activado y las credenciales de MinIO:

```bash
cd scripts && . ../.venv/bin/activate          # la primera vez: python3 -m venv ../.venv && pip install -r requirements.txt
export MINIO_USER=admin MINIO_PASS='<contraseña>'
```

Los nombres de los scripts en inglés (`load.py`, `verify.py`, `probe.py`…) son los que cita el informe y las salidas guardadas en `results/evidencias/`; por eso no se cambiaron.

## Actas de prueba e integridad

| Script | Qué hace | Ejemplo |
|---|---|---|
| `generar_actas.py` | Genera las 1.000 actas de examen ficticias (PDF y texto, unos 390 MB) en `../dataset/actas`. Con la misma semilla salen siempre iguales | `python generar_actas.py` |
| `load.py` | **Carga**: sube las actas a MinIO, registra el SHA-256 de cada una en el servicio de metadatos y escribe el manifiesto `results/manifest.csv` | `python load.py` |
| `verify.py` | **Verificación**: baja cada acta y compara su SHA-256 con el manifiesto. Con `--copia`, además guarda un respaldo | `python verify.py` → `OK: 1000 / 1000` |
| `common.py` | Cliente S3 compartido: si un nodo de MinIO no responde, pasa al siguiente | (lo usan los demás) |

## Experimentos y mediciones

| Script | Qué hace | Ejemplo |
|---|---|---|
| `leader_election.py` | **E2**: mata (o detiene) al líder de etcd y mide cuánto tarda en haber otro y en aceptarse una escritura | `python leader_election.py --modo kill --repeticiones 10` |
| `lock_clients.py` | **E5**: clientes que compiten por el bloqueo de un acta: concurrencia, bloqueo huérfano y fencing token | `python lock_clients.py fencing` |
| `probe.py` | **Sonda**: lecturas y escrituras continuas contra MinIO, etcd o la API mientras dura una falla; anota cada pedido en un CSV | `python probe.py s3 --salida ../results/sonda.csv` |
| `analyze.py` | **Análisis**: de los CSV de la sonda, de E2 y de E5 saca las tablas (disponibilidad, latencia, cortes) y las figuras | `python analyze.py sonda ../results/e4_sonda_s3_1439.csv --eventos ../results/e4_eventos.csv` |
| `medidas.py` | Percentiles y cálculos que comparten la sonda y el análisis | (lo usan los demás) |

Las fallas de E1, E3 y E4 están en [`../chaos/`](../chaos/README.md), y la demo en vivo, en [`../demo/`](../demo/README.md).

## Operación del servidor

| Script | Qué hace | Ejemplo |
|---|---|---|
| `tif` | Prende, apaga y muestra el estado de todo el sistema (VM, monitoreo y API). Instalable en `/usr/local/bin`; el encabezado explica cómo | `scripts/tif estado` |
| `respaldo.sh` | Instantánea de etcd y prueba de restauración en un etcd temporal | `./respaldo.sh etcd` |
| `caidas.py` | Cuándo dejó de responder una VM, según Prometheus, y cómo estaba la memoria antes | `python caidas.py --vm vm3 --horas 8` |
| `watchdog_vms.sh` | Agrega el watchdog a las VM ya creadas y las reinicia de a una | `./watchdog_vms.sh` |
| `probar_watchdog.sh` | Cuelga a propósito el núcleo de una VM y mide cuánto tarda en volver sola | `./probar_watchdog.sh vm4` |

Cada script explica sus opciones con `--help` (los de Python) o en su encabezado (los de shell).
