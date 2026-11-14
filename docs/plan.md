# Plan del TIF: estado y orden de trabajo

Actualizado: 14 de noviembre de 2026.

Referencias: ✅ terminado · 🟡 en curso, con su porcentaje · ⬜ sin empezar · ⛔ trabado (la nota dice por qué)

## Dónde estamos

- **Avance general: alrededor del 93 %.** Es una estimación a ojo, ponderada por área según la tabla de abajo.
- **Ya está hecho:**
  - Todo el código y las herramientas de medición, probados en local y en el clúster.
  - La política de respaldo (sección 6.4 del informe), el runbook de la jornada de caos y la plantilla de post-mortem.
  - **El clúster anda en la laptop (12/11):** 4 VMs, etcd, k3s, MinIO, monitoreo y API, con las 1.000 actas cargadas y verificadas (1.000 de 1.000). Medición base: escritura 6,7 MB/s, lectura 62,8 MB/s.
  - **E2 (12/11):** nuevo líder en 1,5 s de mediana con `kill -9` (de 1,0 a 1,7 s) y en 62 ms con `stop`; en las 10 corridas de cada modo siempre hubo líder nuevo, y la sonda del servicio de metadatos no tuvo errores.
  - **E5 (12/11):** con dos clientes, uno obtiene el bloqueo y el otro recibe 409; si el dueño muere, el bloqueo se libera en 11,85 s de mediana (vence el lease de 15 s); si lo libera, en 0,07 s; el fencing token rechaza al dueño viejo.
  - **Prueba de restauración (12/11):** la instantánea de etcd tiene las 1.000 actas, y la copia de las actas, subida a un bucket nuevo, dio 1.000 de 1.000 en 57 s.
  - **E4 y E3 (13/11, parte A de la jornada):** con la red degradada no falló ningún pedido, pero el p95 de la API pasó de 53 a 1.050 ms y la escritura de una muestra de 20 actas, de 5,6 a 0,2 MB/s. En la partición, la minoría de etcd rechazó las escrituras y no hubo divergencia (402 escrituras confirmadas en los 3 miembros); en MinIO, la mayoría también se demoró más de 5 s mientras esperaba al disco de vm3. Después de cada uno, 1.000 de 1.000.
  - **E1 y verificación final (13/11, parte B de la jornada):** con un nodo caído no se perdieron datos, pero MinIO pasó 58 s sin completar una lectura y después leyó unas seis veces más lento (9,7 MB/s contra 62,8). Con dos nodos caídos, etcd siguió con quórum y el servicio de metadatos no tuvo errores, y MinIO no aceptó escrituras, como se esperaba, pero tampoco sirvió lecturas: los pedidos quedaron esperando, sin errores. La hipótesis esperaba lecturas, así que se refutó en parte: con 4 nodos, el sistema tolera la caída de uno, no la de dos. Verificación final (15:38): 1.000 de 1.000. El reanálisis de E4 sumó la sonda de MinIO: p95 de escritura de 96 a 4.542 ms.
  - **E1-bis (13/11, 19:42 a 19:56):** con los dos nodos apagados en orden, MinIO leyó todo (las 1.000 actas en 4 s); de golpe durante 5 minutos, no leyó nunca. La causa del límite de E1 es la detección de un nodo que muere sin avisar, no el quórum.
  - **Informe (13 y 14/11):** cargados todos los resultados, con 29 figuras; organización del equipo con nombres provisorios («Alumno John», «Alumno 2», «Alumno 3»), bitácoras en borrador (Anexo A), acta de roles (Anexo F), post-mortem citados y bloques de código en 9 pt, sin líneas que se partan.
- **Incidente no planificado (12/11, de 11:28 a 15:48):** vm3 se congeló sola; el sistema siguió andando con 2 de 3 en etcd y 3 de 4 en MinIO. Se recuperó con un reinicio forzado. Acción correctiva: un watchdog en cada VM, probado: una VM congelada vuelve sola en 35 s. Post-mortem: [docs/postmortems/2026-11-12-vm3.md](postmortems/2026-11-12-vm3.md).
- **Sigue:** ensayar la defensa (`guion-defensa.md`, con la demo de un archivo real y `scripts/archivo.py`) y cerrar el informe: nombres, puntajes de la autoevaluación, bitácoras completadas por cada uno, índice y PDF.
- **Falta:**
  - Actualizar el índice al final (John ya lo actualizó una vez el 13/11).
  - Al final: reemplazar los nombres provisorios y completar los puntajes `[__]`; cada integrante revisa su bitácora; ensayo de la demo. El video no hace falta (lo dijo la profesora el 13/11).
  - Decisión del 13/11: el informe queda largo y completo; la versión para la facultad se arma después, aparte.

| Área | Avance | Peso en el total |
|---|---|---|
| A. Servidor (laptop EXO) | 90 % | 10 % |
| B. Código y herramientas | 99 % | 25 % |
| C. Ejecución y mediciones | 97 % | 25 % |
| D. Informe | 97 % | 25 % |
| E. Defensa y entregables | 70 % | 15 % |
| **Total** | **≈ 93 %** | |

## Decisiones tomadas el 11/11

| # | Decisión |
|---|---|
| 1 | Acceso de los compañeros: se les comparte solo la EXO por Tailscale (no se los invita al tailnet). Entran con un usuario `tif` sin sudo, cada uno con su llave SSH |
| 3 | Conjunto de datos: 1.000 actas de examen ficticias, alrededor del 70 % en PDF y el resto en texto, con semilla fija (unos 0,4 GB) |
| 8 | Prometheus y Grafana en el anfitrión con Docker (red host). Chaos Mesh queda solo en el marco teórico: las fallas se inyectan con apagado de VM, iptables y tc netem |
| 12 | El informe describe la EXO con KVM/libvirt como entorno principal; VirtualBox queda como alternativa |
| — | Todo corre en la EXO; la HP y la Acer no se usan. En modo TIF, del homelab queda prendido solo Tailscale |
| — | Rendimiento base con scripts propios: `load.py` (escritura), `verify.py` (lectura) y la sonda (latencia). warp queda opcional |
| — | Versiones fijas: k3s v1.36.6+k3s1, etcd v3.6.16, Prometheus v3.15.1, Grafana 13.2.6, node_exporter v1.12.1 |
| — | MinIO (12/11): `pgsty/minio:RELEASE.2026-08-04T00-00-00Z`, el fork comunitario, porque quay.io dejó de permitir descargas anónimas el 24/09/2026 |
| — | 12/11, después del incidente de vm3: cada VM lleva un watchdog virtual (`i6300esb`, acción `reset`) que systemd atiende cada 15 s; si la VM se congela, QEMU la reinicia sola |
| — | Desde el 12/11, el resto del trabajo lo hace John, que hace de los demás integrantes cuando hace falta (por ejemplo, el compañero que entra desde Windows). Los compañeros podrán probar todo en clase con su guía |

## A. Servidor (laptop EXO): 90 %

| | Actividad | % | Nota |
|---|---|---|---|
| ✅ | Relevamiento del estado de la laptop | 100 % | 11/11 |
| ✅ | Qué se apaga en modo TIF: todo el homelab salvo Tailscale | 100 % | Lo hace el comando `tif` |
| ✅ | Parte 1: KVM/libvirt, Vagrant, Ansible, kubectl, UFW y prueba R12 | 100 % | 11/11: todo bien |
| ✅ | Parte 2: usuario `tif`, comando `tif`, primer arranque del clúster y carga de las actas | 100 % | 12/11. Evidencias en `results/evidencias/` y capturas de los pasos 6, 8 y 9 |
| ✅ | Parte 3: acceso de los compañeros | 95 % | 13/11: probado desde la PC Windows de John (cliente OpenSSH, llave `companero-windows` en `tif`): entra por SSH, `tif estado` anda sin contraseña por la regla `/etc/sudoers.d/tif-comando` (solo `/usr/local/bin/tif`), no tiene otro sudo y ve Grafana. En el informe (sección 7 y Anexo D). Queda compartir la EXO por Tailscale en clase |
| ✅ | Incidente de vm3: diagnóstico y recuperación | 100 % | 12/11. Post-mortem en `docs/postmortems/` |
| ✅ | Watchdog en las 4 VMs | 100 % | 12/11. Aplicado con Ansible (`--tags watchdog`) y `scripts/watchdog_vms.sh`. Probado con `scripts/probar_watchdog.sh`: una VM congelada vuelve sola en 35 s; un pánico común, en 18 s (k3s deja `kernel.panic=10`) |
| ✅ | Parte 4: subir `results/` a GitHub | 100 % | 13/11: John bajó un `.tar.gz` con `scp` y lo adjuntó en el chat; se revisó (solo direcciones de la red de las VM) y se subió (94 archivos). Para resultados nuevos se repite lo mismo |

## B. Código y herramientas: 99 %

| | Actividad | % | Nota |
|---|---|---|---|
| ✅ | Repositorio en GitHub (`Fonspem/TIF-SOD`) | 100 % | |
| ✅ | Vagrantfile (libvirt principal, VirtualBox alternativa) | 100 % | Probado en la laptop con libvirt |
| ✅ | Ansible: base, disco de datos, etcd, k3s, node_exporter y módulo netem | 100 % | Corrió bien en las 4 VMs. El token de k3s ya no aparece en la salida |
| ✅ | Manifiesto de MinIO | 100 % | Desplegado con la imagen `pgsty/minio` |
| ✅ | Servicio de metadatos con bloqueos, lease y fencing, con métricas y 7 pruebas | 100 % | 12/11: corre en el anfitrión y atendió la carga, las sondas y E5 sin errores |
| ✅ | Monitoreo: Prometheus, Grafana con el tablero del Paso 5, node_exporter y la API en Docker | 100 % | Los 17 objetivos `up`. Colores de las líneas de tiempo arreglados. Enlace: `/d/tif-estado` |
| ✅ | Generador de actas, carga con SHA-256 y verificación | 100 % | En el clúster: 1.000 de 1.000 |
| ✅ | Medición de elección de líder (E2) y clientes del bloqueo (E5) | 100 % | 12/11: corridos en el clúster |
| ✅ | Inyección de fallas E1, E3 y E4 | 100 % | 13/11: `chaos/jornada.sh` corrió E4, E3 y E1 en el clúster, cada uno con un comando, y revierte la falla si se corta |
| ✅ | Sonda de estado estable y análisis (tablas y figuras) | 100 % | 12/11: `analyze.py` sacó las tablas de E2 y E5; `--hasta` recorta la corrida abortada de las 14:40. Las figuras salen de `docs/figuras/graficos.py` |
| ✅ | Comando `tif` (prender, apagar y estado, con modo TIF) | 100 % | En la guía de la Parte 2; probado con comandos simulados |
| ✅ | Respaldo: `verify.py --copia` (actas) y `respaldo.sh` (instantánea de etcd y prueba de restauración) | 100 % | 12/11, en el clúster: la instantánea tiene las 1.000 actas y la copia restaurada dio 1.000 de 1.000. `respaldo.sh` cuenta solo las claves `/docs/acta-` (las sondas también registran documentos) |
| ✅ | README para un tercero | 95 % | 13/11: reescrito (resultados, requisitos, `jornada.sh`, respaldo, diagnóstico, problemas conocidos). 14/11: `scripts/tif` genérico y `scripts/archivo.py` (subir y bajar un archivo suelto con su hash, para la demo) |

## C. Ejecución y mediciones: 97 %

| | Actividad | % | Nota |
|---|---|---|---|
| ✅ | Paso 1: levantar las 4 VM y aprovisionarlas | 100 % | 12/11 |
| ✅ | Paso 2: etcd de 3 miembros, más E2 con 10 corridas por modo | 100 % | 12/11. Con `kill -9`, nuevo líder en 1.485 ms de mediana (1.024 a 1.673 ms); con `stop`, en 62 ms (36 a 87 ms). Las sondas no tuvieron errores (2.269 pedidos con `kill -9`, recortados con `--hasta 12:00`, y 2.491 con `stop`). Con `kill -9`, las escrituras durante la elección tardan unos 2 s: el primer miembro consultado no responde dentro de `ETCD_TIMEOUT` y el servicio pasa al siguiente |
| ✅ | Paso 3: MinIO y rendimiento base | 100 % | Escritura 6,7 MB/s y lectura 62,8 MB/s. Latencia p95 en estado estable (sonda, antes de E4): API 53 ms; MinIO 21 ms en lectura y 96 ms en escritura. Capacidad: 42,7 GB brutos y 21,3 GB usables |
| ✅ | Paso 4: servicio de metadatos, demo con dos clientes y E5 | 100 % | 12/11, de 21:08 a 21:11. Bloqueo huérfano: 11,85 s de mediana (11,26 a 12,74 s, cinco corridas); liberado por el dueño: 0,07 s |
| ✅ | Paso 5: generar y cargar las 1.000 actas; tablero de Grafana | 100 % | 1.000 de 1.000 |
| ✅ | Paso 6: jornada de caos (E1, E3 y E4) con las sondas | 100 % | 13/11: E4 y E3 de 14:40 a 14:51; E1 con un nodo y con dos de 15:23 a 15:36. Después de cada uno, 1.000 de 1.000 |
| ✅ | Paso 7: verificación final de los 1.000 hashes | 100 % | 13/11, 15:38: 1.000 de 1.000 con los 4 nodos y los 3 miembros de etcd (`results/verificacion_final.csv`). Antes, 1.000 de 1.000 después del incidente, en la restauración y después de cada experimento |
| ✅ | Capturas de evidencia (Grafana y terminal) | 100 % | 33 capturas en `docs/capturas/` y texto en `results/evidencias/` (en el repo desde el 13/11). Las cuatro de la terminal, con el prompt y la barra de tmux tapados, ya están en el informe (figuras 2, 8, 20 y 22) |

## D. Informe (Google Doc): 93 %

| | Actividad | % | Nota |
|---|---|---|---|
| 🟡 | Portada e índice | 90 % | El índice se actualiza al final (lo hace John): cambiaron el título del Anexo B, se sumaron la 6.4, la 8.5, apartados del 7 y los anexos C a E |
| ✅ | Resumen y palabras clave | 100 % | 13/11: con E1 a E5, el incidente y la verificación final; 248 palabras (APA pide hasta 250) |
| ✅ | 1. Introducción y 2. Objetivos y escenario | 95 % | |
| ✅ | 3. Marco teórico (breve) | 95 % | Se sumaron tc netem e iptables (Hemminger, 2005) |
| ✅ | 4. Herramientas | 100 % | Con las decisiones 8 y 12: Docker en el anfitrión, sin Chaos Mesh, rendimiento con scripts propios |
| 🟡 | 5. Organización del equipo | 80 % | 14/11: tres integrantes con nombres provisorios y roles asignados; faltan los puntajes reales de la autoevaluación (`[__]`) |
| ✅ | 6. Materiales y métodos | 100 % | Con el diagrama de arquitectura (Figura 1, `docs/figuras/arquitectura.dot`) y la decisión del watchdog |
| ✅ | 7. Implementación práctica | 100 % | Con las salidas reales de los pasos 1 a 5, los apartados "Operación del servidor y registro de evidencias" y "Problemas encontrados y soluciones". 14/11: código en Consolas 9 y las líneas largas cortadas |
| ✅ | 8. Resultados | 100 % | E2 (8.1), E5, E4, E3 y E1 (8.2, figuras 9 a 15), integridad y verificación final (8.3), rendimiento y capacidad (8.4) y el incidente de vm3 (8.5); nota sobre el origen de los datos al comienzo. Completo |
| ✅ | 9. Discusión y 10. Conclusiones | 100 % | Con E1 a E5, el incidente (fallas grises), las escrituras ambiguas y las lecciones de operación. E1 refutó en parte su hipótesis: con dos nodos caídos, MinIO no sirvió lecturas |
| 🟡 | Referencias APA | 90 % | Revisar al final |
| ✅ | Política de respaldo | 100 % | Sección 6.4: regla 3-2-1, versionado y bloqueo de objetos, réplica a otra sede e instantáneas de etcd. El resultado de la prueba de restauración está en la 8.3 |
| ✅ | Runbook de la jornada de caos | 100 % | `docs/runbook.md`: controles, criterios para abortar, reversión, respaldo y restauración. El Paso 6 del informe lo cita |
| ✅ | Post-mortem de cada experimento | 100 % | En `docs/postmortems/`: el incidente de vm3 y E1 a E5 (13/11), con la plantilla. 14/11: citados en la sección 7, en la 8.2 y en el Anexo E |
| ✅ | Figuras: arquitectura y resultados de E1 a E5 | 100 % | 29 figuras en el informe. E1 tiene tres capturas del tablero (figuras 14 a 16, con E1-bis) |
| 🟡 | Anexo A: bitácoras | 70 % | 14/11: borrador de las tres (tablas A1 a A3), por etapa, armado con la cronología; cada integrante revisa y agrega qué aprendió y qué le costó |
| ✅ | Anexos C, D y E: decisiones, cronología y evidencias | 100 % | Al día con la jornada de caos completa (13/11) |
| ✅ | Anexo B: variante VirtualBox | 100 % | |
| ⬜ | Exportar a PDF y revisar el formato APA | 0 % | Al final |

## E. Defensa y entregables: 30 %

| | Actividad | % | Nota |
|---|---|---|---|
| 🟡 | Acta de roles y autoevaluación (Paso 0) | 80 % | 14/11: Anexo F del informe (Tabla F1, reglas y firmas); faltan fecha, puntajes y firmas |
| 🟡 | Bitácoras individuales | 70 % | En el Anexo A |
| 🟡 | Presentación para la defensa | 90 % | 18 diapositivas con E1 a E5, E1-bis, el incidente, la integridad y la recomendación; faltan los nombres |
| — | Video de 5 a 8 minutos | — | No hace falta, según la profesora (13/11). El guion queda en el proyecto por si acaso |
| 🟡 | Defensa: pitch, guion y demo | 75 % | 14/11: `guion-defensa.md`: pitch de 40 s, reparto de diapositivas por rol, demo de 5 min con un archivo real (`scripts/archivo.py`), caída del líder y de un nodo, y preguntas probables. Falta ensayarla |

## Orden de trabajo

El camino crítico:
1. ✅ laptop lista (Parte 1);
2. ✅ clúster arriba con las actas cargadas (Parte 2);
3. ✅ E2 y E5 (12/11);
4. ✅ jornada de caos: E4, E3, E1 y la verificación final (13/11);
5. ✅ resultados en el informe, post-mortem citados y código legible (14/11);
6. 🟡 defensa: guion listo; falta el ensayo.

Mientras se prepara la laptop:
- ✅ pasa al informe las decisiones 3, 8 y 12 (11/11);
- ✅ escribe la política de respaldo, el runbook y la plantilla de post-mortem (12/11);
- ✅ hace el diagrama de arquitectura y carga en el informe todo lo del 12/11.

## Recursos de la EXO en modo TIF (estimación del 11/11)

| Recurso | Hay | Usa el TIF | Margen |
|---|---|---|---|
| RAM | 11,4 GB | ~10,1 GB: VMs 8,5 + 0,4 de QEMU, monitoreo y API 0,6, Debian y Tailscale 0,5 | ~1,3 GB, más 6,2 GB de swap |
| Disco | 87 GB libres | 25 a 30 GB | ~55 GB |
| CPU | 4 hilos | 8 vCPU | En las pruebas de rendimiento la CPU es el límite, y eso se informa |

Plan B si la RAM queda justa: bajar vm2 a vm4 de 2 a 1,75 GB.

## Notas de las pruebas locales (para la discusión)

- **Escrituras ambiguas.** En la partición simulada, algunas escrituras se aplicaron igual al reunificar, aunque el cliente las había dado por fallidas por tiempo agotado. Habían quedado en los búferes de TCP y llegaron al líder después.
  - No hubo divergencia: todos los miembros ven lo mismo.
  - Pero un error en el cliente no garantiza que la operación no haya ocurrido.
  - Por eso el servicio de metadatos usa transacciones con comparación: reintentar no rompe nada.
- **Caída del líder y servicio de metadatos.** Con `kill -9` al líder, el servicio no devolvió errores (con un tiempo de espera de 8 s en el cliente). Algunas escrituras tardaron unos 2 s: el primer miembro consultado no respondió dentro de `ETCD_TIMEOUT` y el servicio pasó al siguiente.
- **Minoría aislada.** El miembro aislado rechaza escrituras y lecturas linealizables durante toda la partición. La mayoría solo tiene uno o dos segundos de errores, si tiene que elegir un líder nuevo.
