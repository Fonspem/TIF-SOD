# metadata-service/: servicio de metadatos con bloqueos distribuidos

API REST (Flask) que guarda en etcd los metadatos de cada acta (hash SHA-256, tamaño, estado) y administra los bloqueos para que dos personas no cambien la misma acta a la vez. Corre en el anfitrión, en el puerto 8000; la levanta `monitoring/compose.yaml`.

| Archivo | Qué es |
|---|---|
| `app.py` | El servicio completo |
| `Dockerfile` | Imagen `tif-api:local` |
| `requirements.txt` | Dependencias (Flask, etcd3gw, prometheus-client) |
| `tests/test_app.py` | 7 pruebas contra un etcd real de 3 miembros |

## Qué se le puede pedir

| Pedido | Qué hace |
|---|---|
| `POST /docs/<acta>` | Da de alta un acta en estado «borrador» con su hash, tamaño y objeto. Si ya existe: 409 |
| `GET /docs/<acta>` | Devuelve sus metadatos |
| `POST /docs/<acta>/lock` | Pide el bloqueo: 200 con un *fencing token* y un lease de 15 s, o 409 si lo tiene otro |
| `POST /docs/<acta>/lock/refresh` | Renueva el lease (el dueño lo hace cada 5 s) |
| `PUT /docs/<acta>/state` | Cambia el estado (borrador → firmada → archivada). Exige el token vigente: con uno viejo, 409 |
| `DELETE /docs/<acta>/lock` | Libera el bloqueo |
| `GET /health` | 200 si etcd tiene quórum; 503 si no |
| `GET /metrics` | Métricas para Prometheus |

Variables: `ETCD` (miembros, por defecto los 3 de las VM), `LOCK_TTL` (15 s), `ETCD_TIMEOUT` (2 s por pedido; si un miembro no responde, prueba el siguiente).

## Probarlo

```bash
ETCD_BIN=/ruta/a/etcd pytest -q metadata-service/tests     # levanta un etcd de 3 miembros en 127.0.0.1
python scripts/lock_clients.py concurrencia                 # contra el servicio corriendo: un 200 y un 409
```
