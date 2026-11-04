# Plan de trabajo

Actualizado: 4 de noviembre de 2026. `[x]` hecho, `[ ]` pendiente, `[~]` en curso.

## Decisiones pendientes

- [ ] **Equipo para las mediciones finales:** VirtualBox (variante principal del informe) o la laptop dedicada con KVM (Anexo B).
- [ ] **Dónde corren Prometheus y Grafana:** dentro de k3s (como dice hoy el informe) o en el anfitrión con Docker (consume menos RAM de las VM y no se cae con los experimentos).
- [ ] **Conjunto de datos:** hoy el borrador genera bytes aleatorios; el enunciado pide PDF o texto.

## Código

- [x] Servicio de metadatos con bloqueos, lease y fencing (`metadata-service/`), con 7 pruebas contra un etcd real.
- [x] Medición de la elección de líder, en modos `kill` y `stop` (`scripts/leader_election.py`), probada con etcd local.
- [x] Clientes del bloqueo: concurrencia, bloqueo huérfano (E5) y fencing (`scripts/lock_clients.py`).
- [x] Verificación de hashes con conmutación entre nodos (`scripts/verify.py`), probada con un S3 simulado.
- [x] Vagrantfile con las dos variantes (`vagrant/`).
- [x] Playbook de Ansible: base, disco de datos, etcd y k3s (`ansible/`). Verificación de sintaxis, falta probarlo contra las VM.
- [x] Manifiesto de MinIO con `hostPort` (`k8s/minio.yaml`).
- [x] Inyección de fallas E1, E3 y E4 (`chaos/`).
- [ ] Generador del conjunto de datos y script de carga (espera la decisión sobre el formato).
- [ ] Sonda de estado estable: tráfico continuo con registro de cada pedido.
- [ ] Monitoreo: Prometheus, Grafana y el tablero (espera la decisión sobre dónde corren).
- [ ] Scripts de tablas y gráficos para el informe.

## Con el servidor listo

- [ ] `vagrant up`, `ansible-playbook site.yml` y verificación de etcd y k3s.
- [ ] MinIO desplegado, bucket creado y tolerancia comprobada.
- [ ] Rendimiento base con warp.
- [ ] Carga de los 1.000 documentos con su manifiesto.
- [ ] Mediciones de elección (10 corridas por modo).
- [ ] Experimentos E1 a E5, con post-mortem y verificación de hashes después de cada uno.
- [ ] Verificación final.

## Informe (Google Doc)

- [x] Resumen y palabras clave.
- [x] Correcciones técnicas del borrador (E1, E2, E3, MinIO por nodo, biblioteca de etcd, estado de MinIO).
- [x] Marco teórico: HDFS, Rook, algoritmos por token, Pumba, fio, Ansible, Prometheus y Grafana, de forma breve.
- [x] Fragmentos de código en lugar de listados completos.
- [x] Anexo B: variante para la laptop dedicada.
- [ ] Índice (insertarlo a mano en Google Docs: Insertar → Índice).
- [ ] Resultados, discusión y conclusiones con los datos reales.
- [ ] Organización del equipo, autoevaluaciones y bitácoras.
- [ ] Capturas y figuras.

## Entregables finales

- [ ] Informe en PDF.
- [ ] README probado desde cero.
- [ ] Video de 5 a 8 minutos.
- [ ] Presentación y ensayo de la demo.
