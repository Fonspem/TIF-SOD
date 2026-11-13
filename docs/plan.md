# Plan del TIF: estado y orden de trabajo

Actualizado: 12 de noviembre de 2026.

Referencias: ✅ terminado · 🟡 en curso, con su porcentaje · ⬜ sin empezar · ⛔ trabado (la nota dice por qué)

## Dónde estamos

- **Avance general: alrededor del 70 %.** Es una estimación a ojo, ponderada por área según la tabla de abajo.
- **Ya está hecho:**
  - Todo el código y las herramientas de medición, probados en local y en el clúster.
  - La política de respaldo (sección 6.4 del informe), el runbook de la jornada de caos y la plantilla de post-mortem.
  - **El clúster anda en la laptop (12/11):** 4 VMs, etcd, k3s, MinIO, monitoreo y API, con las 1.000 actas cargadas y verificadas (1.000 de 1.000). Medición base: escritura 6,7 MB/s, lectura 62,8 MB/s.
  - **E2 (12/11):** nuevo líder en 1,5 s de mediana con `kill -9` (de 1,0 a 1,7 s) y en 62 ms con `stop`; en las 10 corridas de cada modo siempre hubo líder nuevo, y la sonda del servicio de metadatos no tuvo errores.
  - **E5 (12/11):** con dos clientes, uno obtiene el bloqueo y el otro recibe 409; si el dueño muere, el bloqueo se libera en 11,85 s de mediana (vence el lease de 15 s); si lo libera, en 0,07 s; el fencing token rechaza al dueño viejo.
  - **Prueba de restauración (12/11):** la instantánea de etcd tiene las 1.000 actas, y la copia de las actas, subida a un bucket nuevo, dio 1.000 de 1.000 en 57 s.
  - **Informe (12/11):** cargados todos los resultados hasta hoy, con 23 figuras, 11 tablas y los anexos C (decisiones), D (cronología) y E (evidencias).
- **Incidente no planificado (12/11, de 11:28 a 15:48):** vm3 se congeló sola; el sistema siguió andando con 2 de 3 en etcd y 3 de 4 en MinIO. Se recuperó con un reinicio forzado. Acción correctiva: un watchdog en cada VM, probado: una VM congelada vuelve sola en 35 s. Post-mortem: [docs/postmortems/2026-11-12-vm3.md](postmortems/2026-11-12-vm3.md).
- **Sigue:** la Parte 3 (acceso de los compañeros), que John empezó el 12/11 a la noche; después, la jornada de caos (E1, E3 y E4).
- **Falta:**
  - La jornada de caos (E1, E3 y E4) y la verificación final.
  - Completar el informe con esos resultados, recortar cuatro capturas de la terminal y actualizar el índice.
  - Armar los entregables de la defensa.

| Área | Avance | Peso en el total |
|---|---|---|
| A. Servidor (laptop EXO) | 80 % | 10 % |
| B. Código y herramientas | 97 % | 25 % |
| C. Ejecución y mediciones | 65 % | 25 % |
| D. Informe | 85 % | 25 % |
| E. Defensa y entregables | 0 % | 15 % |
| **Total** | **≈ 70 %** | |

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
| — | Desde el 12/11, el resto del trabajo lo hacen John y el equipo; John hace de los demás integrantes cuando hace falta (por ejemplo, el compañero que entra desde Windows). Los compañeros podrán probar todo en clase con su guía |

## A. Servidor (laptop EXO): 80 %

| | Actividad | % | Nota |
|---|---|---|---|
| ✅ | Relevamiento del estado de la laptop | 100 % | 11/11 |
| ✅ | Qué se apaga en modo TIF: todo el homelab salvo Tailscale | 100 % | Lo hace el comando `tif` |
| ✅ | Parte 1: KVM/libvirt, Vagrant, Ansible, kubectl, UFW y prueba R12 | 100 % | 11/11: todo bien |
| ✅ | Parte 2: usuario `tif`, comando `tif`, primer arranque del clúster y carga de las actas | 100 % | 12/11. Evidencias en `results/evidencias/` y capturas de los pasos 6, 8 y 9 |
| 🟡 | Parte 3: acceso de los compañeros | 20 % | Guía escrita (12/11): se simula un compañero desde la PC Windows de John; la invitación de Tailscale queda para la clase. Hay una guía aparte para los compañeros, sin datos privados. John la empezó el 12/11 a la noche |
| ✅ | Incidente de vm3: diagnóstico y recuperación | 100 % | 12/11. Post-mortem en `docs/postmortems/` |
| ✅ | Watchdog en las 4 VMs | 100 % | 12/11. Aplicado con Ansible (`--tags watchdog`) y `scripts/watchdog_vms.sh`. Probado con `scripts/probar_watchdog.sh`: una VM congelada vuelve sola en 35 s; un pánico común, en 18 s (k3s deja `kernel.panic=10`) |
| ⬜ | Parte 4: subir los resultados a GitHub desde la EXO (llave de despliegue) | 0 % | Después de la Parte 3. Antes de subir `results/evidencias/`, revisar que no tenga datos privados de la red |

## B. Código y herramientas: 97 %

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
| 🟡 | Inyección de fallas E1, E3 y E4 | 80 % | Falta correrla en el clúster |
| ✅ | Sonda de estado estable y análisis (tablas y figuras) | 100 % | 12/11: `analyze.py` sacó las tablas de E2 y E5; `--hasta` recorta la corrida abortada de las 14:40. Las figuras salen de `docs/figuras/graficos.py` |
| ✅ | Comando `tif` (prender, apagar y estado, con modo TIF) | 100 % | En la guía de la Parte 2; probado con comandos simulados |
| ✅ | Respaldo: `verify.py --copia` (actas) y `respaldo.sh` (instantánea de etcd y prueba de restauración) | 100 % | 12/11, en el clúster: la instantánea tiene las 1.000 actas y la copia restaurada dio 1.000 de 1.000. `respaldo.sh` cuenta solo las claves `/docs/acta-` (las sondas también registran documentos) |
| 🟡 | README probado desde cero | 85 % | La Parte 2 siguió sus pasos; falta revisarlo entero al final |

## C. Ejecución y mediciones: 65 %

| | Actividad | % | Nota |
|---|---|---|---|
| ✅ | Paso 1: levantar las 4 VM y aprovisionarlas | 100 % | 12/11 |
| ✅ | Paso 2: etcd de 3 miembros, más E2 con 10 corridas por modo | 100 % | 12/11. Con `kill -9`, nuevo líder en 1.485 ms de mediana (1.024 a 1.673 ms); con `stop`, en 62 ms (36 a 87 ms). Las sondas no tuvieron errores (2.269 pedidos con `kill -9`, recortados con `--hasta 12:00`, y 2.491 con `stop`). Con `kill -9`, las escrituras durante la elección tardan unos 2 s: el primer miembro consultado no responde dentro de `ETCD_TIMEOUT` y el servicio pasa al siguiente |
| 🟡 | Paso 3: MinIO y rendimiento base | 70 % | Escritura 6,7 MB/s y lectura 62,8 MB/s; falta la latencia con la sonda |
| ✅ | Paso 4: servicio de metadatos, demo con dos clientes y E5 | 100 % | 12/11, de 21:08 a 21:11. Bloqueo huérfano: 11,85 s de mediana (11,26 a 12,74 s, cinco corridas); liberado por el dueño: 0,07 s |
| ✅ | Paso 5: generar y cargar las 1.000 actas; tablero de Grafana | 100 % | 1.000 de 1.000 |
| ⬜ | Paso 6: jornada de caos (E1, E3 y E4) con las sondas | 0 % | |
| 🟡 | Paso 7: verificación final de los 1.000 hashes | 30 % | Verificaciones intermedias: 1.000 de 1.000 después del incidente (16:17) y en la prueba de restauración (21:15). Falta la final, después de la jornada de caos |
| 🟡 | Capturas de evidencia (Grafana y terminal) | 70 % | 20 capturas en `docs/capturas/` y texto en `results/evidencias/`. Cuatro capturas de la terminal esperan que John recorte el nombre del equipo y la IP de la casa antes de ir al informe |

## D. Informe (Google Doc): 85 %

| | Actividad | % | Nota |
|---|---|---|---|
| 🟡 | Portada e índice | 90 % | El índice se actualiza al final (lo hace John): cambiaron el título del Anexo B, se sumaron la 6.4, la 8.5, apartados del 7 y los anexos C a E |
| 🟡 | Resumen y palabras clave | 90 % | Con los resultados de E2, E5, el incidente y la restauración. Faltan E1, E3 y E4, y recortarlo: tiene 277 palabras y APA pide hasta 250 |
| ✅ | 1. Introducción y 2. Objetivos y escenario | 95 % | |
| ✅ | 3. Marco teórico (breve) | 95 % | Se sumaron tc netem e iptables (Hemminger, 2005) |
| ✅ | 4. Herramientas | 100 % | Con las decisiones 8 y 12: Docker en el anfitrión, sin Chaos Mesh, rendimiento con scripts propios |
| 🟡 | 5. Organización del equipo | 20 % | Faltan nombres, roles y autoevaluación |
| ✅ | 6. Materiales y métodos | 100 % | Con el diagrama de arquitectura (Figura 1, `docs/figuras/arquitectura.dot`) y la decisión del watchdog |
| 🟡 | 7. Implementación práctica | 90 % | Con las salidas reales de los pasos 1 a 5, los apartados "Operación del servidor y registro de evidencias" y "Problemas encontrados y soluciones" (14 problemas). Falta una captura recortada (Figura 2) y acortar las líneas largas de los bloques de código de los pasos 2 a 4 y de E3, que se cortan en el PDF |
| 🟡 | 8. Resultados | 65 % | E2 (8.1), E5 (8.2), integridad y restauración (8.3), rendimiento (8.4) y el incidente de vm3 (8.5). Siguen los huecos [medir] de E1, E3 y E4 y tres capturas recortadas (figuras 8, 15 y 17) |
| 🟡 | 9. Discusión y 10. Conclusiones | 75 % | Con E2, E5, el incidente (fallas grises) y las lecciones de operación. Faltan E1, E3 y E4 |
| 🟡 | Referencias APA | 90 % | Revisar al final |
| ✅ | Política de respaldo | 100 % | Sección 6.4: regla 3-2-1, versionado y bloqueo de objetos, réplica a otra sede e instantáneas de etcd. El resultado de la prueba de restauración está en la 8.3 |
| ✅ | Runbook de la jornada de caos | 100 % | `docs/runbook.md`: controles, criterios para abortar, reversión, respaldo y restauración. El Paso 6 del informe lo cita |
| 🟡 | Post-mortem de cada experimento | 20 % | Plantilla lista (`docs/postmortem-plantilla.md`). Primero escrito: el incidente de vm3 (`docs/postmortems/2026-11-12-vm3.md`), cerrado con la prueba del watchdog. Va al informe (resultados y discusión) |
| 🟡 | Figuras: arquitectura y resultados de E1 a E5 | 70 % | Arquitectura, E2, E5 y el incidente, en `docs/figuras/`; 23 figuras en el informe. Faltan las de E1, E3 y E4 |
| ⬜ | Anexo A: bitácoras | 0 % | Plantilla lista (Tabla A1) |
| ✅ | Anexos C, D y E: decisiones, cronología y evidencias | 100 % | 12/11. Se actualizan con la jornada de caos |
| ✅ | Anexo B: variante VirtualBox | 100 % | |
| ⬜ | Exportar a PDF y revisar el formato APA | 0 % | Al final |

## E. Defensa y entregables: 0 %

| | Actividad | % | Nota |
|---|---|---|---|
| ⬜ | Acta de roles y autoevaluación (Paso 0) | 0 % | Necesita los nombres |
| ⬜ | Bitácoras individuales | 0 % | |
| ⬜ | Presentación para la defensa | 0 % | Cuando haya resultados |
| ⬜ | Video de 5 a 8 minutos | 0 % | Conviene grabar tramos durante la jornada de caos |
| ⬜ | Demo en vivo: guion y ensayo | 0 % | Carga, caída de un nodo y del líder, partición y verificación |

## Orden de trabajo

El camino crítico:
1. ✅ laptop lista (Parte 1);
2. ✅ clúster arriba con las actas cargadas (Parte 2);
3. ✅ E2 y E5 (12/11);
4. jornada de caos (E1, E3 y E4);
5. resultados en el informe;
6. defensa.

Mientras John prepara la laptop, el equipo:
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
