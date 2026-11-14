# Versiones instaladas

Las versiones fijas están en el repositorio (`ansible/group_vars/all.yml`, `k8s/minio.yaml` y
`monitoring/compose.yaml`). Las del anfitrión salen del relevamiento de la laptop del 11/11/2026.

## Anfitrión

| Componente | Versión |
|---|---|
| Laptop | Intel Core i3-1005G1 (2 núcleos, 4 hilos), 12 GB de RAM, SSD de 119 GiB |
| Sistema operativo | Debian 13 |
| Hipervisor | KVM con libvirt 11.3.0 y QEMU 10.0.13 |
| Vagrant | 2.3.8 (paquete de Debian) con el plugin vagrant-libvirt 0.12.2 |
| Ansible | ansible-core 2.22 |
| kubectl | v1.36.6 |
| Docker | 29.9.2, con Compose v5.6.0 |
| Python | 3.13.5 |

## Máquinas virtuales

| Componente | Versión |
|---|---|
| Box | `bento/ubuntu-24.04` (proveedor libvirt, 202508.03.0) |
| k3s | v1.36.6+k3s1 |
| etcd | v3.6.16 |
| MinIO | `docker.io/pgsty/minio:RELEASE.2026-08-04T00-00-00Z`, fork comunitario de Pigsty (quay.io dejó de permitir descargas anónimas de `quay.io/minio/minio` el 24/09/2026) |
| node_exporter de las VM | 1.7.0 (paquete `prometheus-node-exporter` 1.7.0-1ubuntu0.3 de Ubuntu 24.04) |

## Monitoreo y servicio de metadatos (Docker, en el anfitrión)

| Componente | Versión |
|---|---|
| Prometheus | v3.15.1 |
| Grafana | 13.2.6 |
| node_exporter del anfitrión | v1.12.1 |
| Imagen base del servicio de metadatos | `python:3.13-slim` |
| etcd3gw | 2.7.0 (`pip show etcd3gw` en la imagen `tif-api:local`, 13/11/2026) |
