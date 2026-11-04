# TIF SOD 2026 · Propuesta C: repositorio académico distribuido y tolerante a fallos

Prototipo de repositorio documental para una universidad con varias sedes. El contenido de los documentos se guarda en **MinIO** distribuido (codificación de borrado sobre 4 nodos); el estado de cada documento y los bloqueos, en un clúster **etcd** de 3 miembros (consenso Raft). Un **servicio de metadatos** impide que dos usuarios modifiquen a la vez el mismo documento, con bloqueos atados a un *lease* y *fencing tokens*. Sobre esa base se ejecutan experimentos de **ingeniería del caos** y se verifica la integridad de los documentos con SHA-256.

Trabajo Integrador Final de Sistemas Operativos Distribuidos, Facultad de Ingeniería, Tecnología y Arquitectura.

## Estructura

| Carpeta | Contenido |
|---|---|
| `vagrant/` | Vagrantfile de las 4 VM, con dos variantes: VirtualBox (principal) y KVM/libvirt (laptop dedicada) |
| `ansible/` | Aprovisionamiento: paquetes, disco de datos, etcd (systemd) y k3s |
| `k8s/` | Manifiesto de MinIO distribuido |
| `metadata-service/` | API REST de metadatos con bloqueos (Flask + etcd3gw) y sus pruebas |
| `scripts/` | Medición de elecciones de etcd, clientes del bloqueo (E5, fencing), verificación de hashes |
| `chaos/` | Inyección de fallas: caída de nodo (E1), partición (E3), red degradada (E4) |
| `results/` | Datos crudos de los experimentos (CSV) |
| `docs/` | Plan de trabajo y versiones instaladas |

## Arquitectura

```
                     red privada 192.168.56.0/24
  vm1 (.11)              vm2 (.12)          vm3 (.13)          vm4 (.14)
  k3s server             k3s agent          k3s agent          k3s agent
  etcd-1                 etcd-2             etcd-3             -
  minio-0                minio-1            minio-2            minio-3

  Anfitrión: servicio de metadatos (puerto 5000), scripts de carga, verificación y medición
```

- etcd corre como servicio systemd, separado del almacén interno de k3s, para poder detener a su líder sin afectar a Kubernetes.
- MinIO forma un único conjunto de borrado de 4 unidades (EC:2): lee con 2 unidades y escribe con 3.
- Cada pod de MinIO expone el puerto 9000 en su nodo (`hostPort`), para hablarle a una unidad concreta.

## Cómo levantarlo

Requisitos del anfitrión: Vagrant con VirtualBox (o con KVM/libvirt y el plugin vagrant-libvirt), Ansible, kubectl y Python 3.11 o superior.

```bash
# 1. Máquinas virtuales
cd vagrant
vagrant up                        # o: vagrant up --provider=libvirt
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
mc alias set lab http://192.168.56.11:9000 admin '<contraseña>'
mc mb lab/actas
mc admin info lab                 # 4/4 unidades en línea

# 4. Servicio de metadatos (en el anfitrión)
cd ../metadata-service
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
python app.py                     # escucha en el puerto 5000
```

## Experimentos

```bash
cd scripts && pip install -r requirements.txt

# Paso 2 / E2: elección de líder de etcd, 10 corridas por modo
python leader_election.py --modo kill --repeticiones 10 --salida ../results/e2_kill.csv
python leader_election.py --modo stop --repeticiones 10 --salida ../results/e2_stop.csv

# Paso 4 / E5: exclusión mutua, bloqueo huérfano y fencing
python lock_clients.py concurrencia --clientes 2
python lock_clients.py huerfano --repeticiones 5 --salida ../results/e5_kill.csv
python lock_clients.py fencing

# E1, E3 y E4
cd ../chaos
./e1_caida_nodo.sh apagar vm4 && ./e1_caida_nodo.sh encender vm4
./e3_particion.sh aislar vm3  && ./e3_particion.sh revertir vm3
kubectl apply -f e4-netem.yaml    # o: ./e4_netem.sh aplicar / revertir

# Paso 7: verificación de los hashes
cd ../scripts && MINIO_USER=admin MINIO_PASS='<contraseña>' python verify.py
```

## Pruebas del servicio de metadatos

Levantan un clúster etcd real de 3 miembros en la máquina local:

```bash
ETCD_BIN=/ruta/a/etcd python -m pytest -q metadata-service/tests
```

## Estado

Ver [docs/plan.md](docs/plan.md).
