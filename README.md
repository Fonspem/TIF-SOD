# TIF SOD 2026 · Propuesta C: repositorio académico distribuido y tolerante a fallos

Prototipo de repositorio documental para una universidad con varias sedes. El contenido de los documentos se guarda en **MinIO** distribuido (codificación de borrado sobre 4 nodos); el estado de cada documento y los bloqueos, en un clúster **etcd** de 3 miembros (consenso Raft). Un **servicio de metadatos** impide que dos usuarios modifiquen a la vez el mismo documento, con bloqueos atados a un *lease* y *fencing tokens*. Sobre esa base se ejecutan experimentos de **ingeniería del caos** y se verifica la integridad de los documentos con SHA-256.

Trabajo Integrador Final de Sistemas Operativos Distribuidos, Facultad de Ingeniería, Tecnología y Arquitectura.

## Estructura

| Carpeta | Contenido |
|---|---|
| `vagrant/` | Vagrantfile de las 4 VM: KVM/libvirt en la laptop dedicada (principal) o VirtualBox (alternativa) |
| `ansible/` | Aprovisionamiento: paquetes, disco de datos, etcd (systemd), k3s y node_exporter |
| `k8s/` | Manifiesto de MinIO distribuido |
| `metadata-service/` | API REST de metadatos con bloqueos (Flask + etcd3gw), sus pruebas y su imagen Docker |
| `monitoring/` | Prometheus, Grafana (con el tablero del TIF), node_exporter del anfitrión y la API, con Docker Compose |
| `scripts/` | Generación y carga de las 1.000 actas, verificación de hashes, medición de elecciones de etcd, clientes del bloqueo (E5, fencing), sonda de estado estable, tablas y figuras, respaldo de etcd |
| `chaos/` | Inyección de fallas: caída de nodo (E1), partición (E3), red degradada (E4) |
| `results/` | Datos crudos de los experimentos (CSV) |
| `docs/` | Plan de trabajo, versiones instaladas, [runbook](docs/runbook.md) de la jornada de caos y [plantilla de post-mortem](docs/postmortem-plantilla.md) |

## Arquitectura

```
                     red privada 192.168.56.0/24
  vm1 (.11)              vm2 (.12)          vm3 (.13)          vm4 (.14)
  k3s server             k3s agent          k3s agent          k3s agent
  etcd-1                 etcd-2             etcd-3             -
  minio-0                minio-1            minio-2            minio-3

  Anfitrión (Docker, red host): API de metadatos :8000 · Prometheus :9090 · Grafana :3000
  Anfitrión: scripts de carga, verificación, medición y caos
```

- etcd corre como servicio systemd, separado del almacén interno de k3s, para poder detener a su líder sin afectar a Kubernetes.
- MinIO forma un único conjunto de borrado de 4 unidades (EC:2): lee con 2 unidades y escribe con 3.
- Cada pod de MinIO expone el puerto 9000 en su nodo (`hostPort`), para hablarle a una unidad concreta.

## Cómo levantarlo

Requisitos del anfitrión: Vagrant con KVM/libvirt y el plugin vagrant-libvirt (o con VirtualBox), Ansible, kubectl 1.36, Docker con Compose y Python 3.11 o superior.

```bash
# 1. Máquinas virtuales
cd vagrant
vagrant up --provider=libvirt     # o: vagrant up --provider=virtualbox
vagrant ssh-config > ../ansible/ssh_config

# 2. Aprovisionamiento (etcd y k3s)
cd ../ansible
K3S_TOKEN='<token-largo>' ansible-playbook site.yml
export KUBECONFIG=$PWD/../kubeconfig
kubectl get nodes                 # 4 nodos Ready
ssh -F ssh_config vm1 'etcdctl --endpoints=192.168.56.11:2379,192.168.56.12:2379,192.168.56.13:2379 endpoint status -w table'

# 3. MinIO
kubectl create namespace minio
kubectl -n minio create secret generic minio-creds \
  --from-literal=MINIO_ROOT_USER=admin --from-literal=MINIO_ROOT_PASSWORD='<contraseña>'
kubectl apply -f ../k8s/minio.yaml
kubectl -n minio get pods -o wide                       # 4 pods Running, uno por VM
curl -s -o /dev/null -w '%{http_code}\n' http://192.168.56.11:9000/minio/health/cluster   # 200: hay quórum de escritura

# 4. Monitoreo y API de metadatos (Docker en el anfitrión, red host)
cd ../monitoring
cp .env.example .env              # y poner la contraseña de Grafana
docker compose up -d --build      # Grafana :3000 (tablero "TIF · Estado del sistema"), Prometheus :9090, API :8000
# El tablero se abre directo en http://<anfitrión>:3000/d/tif-estado (también: Dashboards > TIF)

# 5. Actas de prueba: generar, subir y verificar (el bucket se crea solo)
cd ../scripts
python3 -m venv ../.venv && . ../.venv/bin/activate && pip install -r requirements.txt
export MINIO_USER=admin MINIO_PASS='<contraseña>'
python generar_actas.py           # 1.000 actas ficticias (PDF y texto, ~0,4 GB) en ../dataset/actas
python load.py                    # sube, registra cada SHA-256 y escribe ../results/manifest.csv (MB/s de escritura)
python verify.py                  # baja todo y compara los hashes (MB/s de lectura)
```

## Experimentos

Todo se corre desde `scripts/`. Los scripts de `chaos/` y `leader_election.py` anotan la hora de cada falla en `results/eN_eventos.csv`; la **sonda** (`probe.py`) hace una lectura y una escritura cada 0,5 s y anota cada pedido, así después se cruzan las dos cosas. La sonda se arranca antes de inyectar la falla y se corta con Ctrl+C (o `kill`) cuando el sistema volvió al estado estable.

El guion completo de la jornada está en el [runbook](docs/runbook.md): controles antes de cada falla, criterios para abortar, cómo revertir cada una, y el respaldo y la prueba de restauración. Cada experimento cierra con un post-mortem según la [plantilla](docs/postmortem-plantilla.md).

```bash
cd scripts && pip install -r requirements.txt
export MINIO_USER=admin MINIO_PASS='<contraseña>'

# Paso 2 / E2: elección de líder de etcd, 10 corridas por modo.
# En otra terminal, la sonda mide las solicitudes fallidas del servicio de metadatos.
python probe.py meta --etiqueta e2-kill --intervalo 0.1 --salida ../results/e2_sonda_meta_kill.csv
python leader_election.py --modo kill --repeticiones 10 --salida ../results/e2_kill.csv
python leader_election.py --modo stop --repeticiones 10 --salida ../results/e2_stop.csv

# Paso 4 / E5: exclusión mutua, bloqueo huérfano y fencing
python lock_clients.py concurrencia --clientes 2
python lock_clients.py huerfano --repeticiones 5 --salida ../results/e5_kill.csv
python lock_clients.py huerfano --ordenado --repeticiones 5 --salida ../results/e5_ordenado.csv
python lock_clients.py fencing

# E1: caída de un nodo, con la sonda corriendo en otra terminal
python probe.py s3 --etiqueta e1 --salida ../results/e1_sonda_s3.csv
../chaos/e1_caida_nodo.sh apagar vm4       # observar un par de minutos
../chaos/e1_caida_nodo.sh encender vm4

# E3: partición. Una sonda por lado, contra etcd y contra MinIO.
python probe.py etcd --nodos 192.168.56.13:2379 --etiqueta e3-vm3 --salida ../results/e3_etcd_vm3.csv &
python probe.py etcd --nodos 192.168.56.11:2379 --etiqueta e3-vm1 --salida ../results/e3_etcd_vm1.csv &
python probe.py s3 --nodos http://192.168.56.13:9000 --etiqueta e3-vm3 --salida ../results/e3_s3_vm3.csv &
python probe.py s3 --nodos http://192.168.56.11:9000 --etiqueta e3-vm1 --salida ../results/e3_s3_vm1.csv &
../chaos/e3_particion.sh aislar vm3; sleep 60; ../chaos/e3_particion.sh revertir vm3; sleep 30; kill %1 %2 %3 %4
# Consistencia final: qué escrituras ve cada nodo después de reunificar
python probe.py etcd --comprobar ../results/e3_etcd_vm1.csv ../results/e3_etcd_vm3.csv
python probe.py s3 --comprobar ../results/e3_s3_vm1.csv ../results/e3_s3_vm3.csv

# E4: red degradada (tc netem; con Chaos Mesh, anotar a mano la hora en results/e4_eventos.csv)
python probe.py s3 --etiqueta e4 --salida ../results/e4_sonda_s3.csv &
../chaos/e4_netem.sh aplicar; sleep 300; ../chaos/e4_netem.sh revertir; sleep 60; kill %1

# Paso 7: verificación de los hashes
python verify.py
```

### Tablas y figuras para el informe

`analyze.py` imprime tablas en Markdown, con coma decimal, y guarda cada figura en PNG:

```bash
python analyze.py eleccion ../results/e2_kill.csv ../results/e2_stop.csv --figura ../results/figuras/e2.png
python analyze.py sonda ../results/e2_sonda_meta_kill.csv --eventos ../results/e2_eventos.csv --por-accion \
    --figura ../results/figuras/e2_meta.png
python analyze.py sonda ../results/e1_sonda_s3.csv --eventos ../results/e1_eventos.csv --figura ../results/figuras/e1.png
python analyze.py sonda ../results/e3_etcd_vm1.csv ../results/e3_etcd_vm3.csv --eventos ../results/e3_eventos.csv \
    --figura ../results/figuras/e3_etcd.png
python analyze.py sonda ../results/e4_sonda_s3.csv --eventos ../results/e4_eventos.csv --figura ../results/figuras/e4.png
python analyze.py huerfano ../results/e5_kill.csv ../results/e5_ordenado.csv --figura ../results/figuras/e5.png
```

Para cada experimento salen la disponibilidad, la latencia p50 y p95 y el corte más largo por tramo (antes, durante y después de la falla), y, para cada evento, cuánto tardó en aparecer el primer error y cuánto en recuperarse el servicio.

## Pruebas del servicio de metadatos

Levantan un clúster etcd real de 3 miembros en la máquina local:

```bash
ETCD_BIN=/ruta/a/etcd python -m pytest -q metadata-service/tests
```

## Estado

Ver [docs/plan.md](docs/plan.md).
