# ansible/: aprovisionamiento de las 4 VM

Un solo playbook, `site.yml`, deja las VM listas: paquetes base, hora sincronizada, node_exporter, el disco de datos de MinIO, el módulo netem (E4), el watchdog, etcd con 3 miembros (systemd, fuera de k3s) y k3s (vm1 servidor, vm2 a vm4 agentes).

| Archivo | Qué es |
|---|---|
| `site.yml` | El playbook |
| `inventory.ini` | Las 4 VM y qué rol tiene cada una (etcd, servidor o agente de k3s) |
| `group_vars/all.yml` | Versiones fijas (etcd, k3s) y parámetros (tiempos de etcd, disco de datos) |
| `templates/` | Configuración y unidad systemd de etcd |
| `ansible.cfg` | Usa `ssh_config` (lo genera Vagrant; no se versiona) |

```bash
cd vagrant && vagrant ssh-config | sed 's/LogLevel FATAL/LogLevel ERROR/' > ../ansible/ssh_config
cd ../ansible && K3S_TOKEN='<token-largo>' ansible-playbook site.yml
ansible-playbook site.yml --tags watchdog        # solo el watchdog, en VM ya creadas
```

Deja `kubeconfig` en la raíz del repositorio para usar `kubectl` desde el anfitrión.
