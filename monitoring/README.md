# monitoring/: Prometheus, Grafana y la API, en el anfitrión

Todo con Docker Compose y red del anfitrión (así los puertos quedan detrás del firewall; ver «Problemas conocidos» en el README principal).

| Archivo | Qué es |
|---|---|
| `compose.yaml` | Prometheus (:9090), Grafana (:3000), node_exporter del anfitrión (:9100) y el servicio de metadatos (:8000) |
| `prometheus.yml` | Qué mide: etcd, MinIO (por nodo y del clúster), node_exporter de cada VM y del anfitrión, y la API |
| `grafana/dashboards/tif.json` | El tablero «TIF · Estado del sistema»: nodos arriba, líder de etcd, discos de MinIO, latencia, errores y recursos |
| `grafana/provisioning/` | Carga sola la fuente de datos y el tablero al arrancar |
| `.env.example` | Copiar a `.env` y poner la contraseña de Grafana |

```bash
cd monitoring && cp .env.example .env     # y editar la contraseña
docker compose up -d --build
```

El tablero se abre directo en `http://<anfitrión>:3000/d/tif-estado`.
