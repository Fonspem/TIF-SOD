# Plan de trabajo

Actualizado: 4 de noviembre de 2026. `[x]` hecho, `[ ]` pendiente, `[~]` en curso.

## Decisiones pendientes

- [ ] **Equipo para las mediciones finales:** VirtualBox (variante principal del informe) o la laptop dedicada con KVM (Anexo B).
- [ ] **Dónde corren Prometheus y Grafana:** dentro de k3s (como dice hoy el informe) o en el anfitrión con Docker (consume menos RAM de las VM y no se cae con los experimentos).
- [ ] **Conjunto de datos:** hoy el borrador genera bytes aleatorios; el enunciado pide PDF o texto.

## Código

- [x] Servicio de metadatos con bloqueos, lease y fencing (`metadata-service/`), con 7 pruebas contra un etcd real.
- [x] Medición de la elección de líder, en modos `kill` y `stop` (`scripts/leader_election.py`), probada con etcd local. Anota cada caída en `results/e2_eventos.csv`.
- [x] Clientes del bloqueo: concurrencia, bloqueo huérfano (E5) y fencing (`scripts/lock_clients.py`).
- [x] Verificación de hashes con conmutación entre nodos (`scripts/verify.py`), probada con un S3 simulado.
- [x] Vagrantfile con las dos variantes (`vagrant/`).
- [x] Playbook de Ansible: base, disco de datos, etcd y k3s (`ansible/`). Verificación de sintaxis, falta probarlo contra las VM.
- [x] Manifiesto de MinIO con `hostPort` (`k8s/minio.yaml`).
- [x] Inyección de fallas E1, E3 y E4 (`chaos/`).
- [ ] Generador del conjunto de datos y script de carga (espera la decisión sobre el formato).
- [x] Sonda de estado estable (`scripts/probe.py`): lecturas y escrituras periódicas contra MinIO, etcd o el servicio de metadatos, con registro de cada pedido y comprobación de consistencia final para E3. Probada con etcd local (caída del líder y partición simulada con iptables), con el servicio de metadatos y con un S3 simulado.
- [ ] Monitoreo: Prometheus, Grafana y el tablero (espera la decisión sobre dónde corren).
- [x] Tablas y figuras para el informe (`scripts/analyze.py`): sonda (E1 a E4), elección de líder (E2) y bloqueo huérfano (E5).

## Notas de las pruebas locales (para la discusión)

- **Escrituras ambiguas.** En la partición simulada, algunas escrituras que el cliente dio por fallidas (tiempo agotado) se aplicaron igual al reunificar: quedaron en los búferes de TCP y llegaron al líder después. No hay divergencia (todos los miembros ven lo mismo), pero un error en el cliente no garantiza que la operación no haya ocurrido. Por eso el servicio de metadatos usa transacciones con comparación: reintentar no rompe nada.
- **Caída del líder y servicio de metadatos.** Con `kill -9` al líder, el servicio no devolvió errores (con un tiempo de espera de 8 s en el cliente), pero algunas escrituras tardaron unos 2 s: el primer miembro consultado no respondió dentro de `ETCD_TIMEOUT` y el servicio pasó al siguiente.
- **Minoría aislada.** El miembro aislado rechaza lecturas linealizables y escrituras durante toda la partición; la mayoría sólo tiene uno o dos segundos de errores si tiene que elegir un líder nuevo.

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
