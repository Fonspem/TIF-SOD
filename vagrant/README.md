# vagrant/: las 4 máquinas virtuales

`Vagrantfile` crea vm1 a vm4 en la red privada 192.168.56.0/24, con 2 vCPU cada una:

| VM | IP | RAM (libvirt) | Qué corre |
|---|---|---|---|
| vm1 | 192.168.56.11 | 2,5 GB | servidor de k3s, etcd 1, MinIO (`minio-3`) |
| vm2 | 192.168.56.12 | 2 GB | agente de k3s, etcd 2, MinIO (`minio-2`) |
| vm3 | 192.168.56.13 | 2 GB | agente de k3s, etcd 3, MinIO (`minio-1`) |
| vm4 | 192.168.56.14 | 2 GB | agente de k3s, MinIO (`minio-0`) |

Con libvirt (principal) cada VM tiene un disco de datos aparte para MinIO y un watchdog que la reinicia si se congela. VirtualBox queda como alternativa (Ubuntu 22.04, sin disco aparte).

```bash
vagrant up --provider=libvirt        # o: vagrant up --provider=virtualbox
vagrant halt                          # apagado ordenado
```
