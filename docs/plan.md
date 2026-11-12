# Plan del TIF: estado y orden de trabajo

Actualizado: 11 de noviembre de 2026.

Referencias: ✅ terminado · 🟡 en curso, con su porcentaje · ⬜ sin empezar · ⛔ trabado (la nota dice por qué)

## Dónde estamos

- **Avance general: alrededor del 40 %.** Es una estimación a ojo, ponderada por área según la tabla de abajo.
- **Ya está hecho:**
  - Todo el código y las herramientas de medición, probados en local.
  - El borrador del informe completo, salvo los resultados.
- **En curso:** la Parte 2 de la guía del host: usuario `tif`, primer arranque del clúster y carga de las actas. La Parte 1 terminó bien, prueba R12 incluida.
- **Falta:**
  - Levantar el clúster y correr los experimentos.
  - Completar el informe con los resultados. Las decisiones del 11/11 ya están en el informe.
  - Armar los entregables de la defensa.
- **El cuello de botella sigue siendo la laptop.** Todo lo que no depende de ella ya está hecho o en marcha.

| Área | Avance | Peso en el total |
|---|---|---|
| A. Servidor (laptop EXO) | 40 % | 10 % |
| B. Código y herramientas | 85 % | 25 % |
| C. Ejecución y mediciones | 0 % | 25 % |
| D. Informe | 65 % | 25 % |
| E. Defensa y entregables | 0 % | 15 % |
| **Total** | **≈ 40 %** | |

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

## A. Servidor (laptop EXO): 40 %

| | Actividad | % | Nota |
|---|---|---|---|
| ✅ | Relevamiento del estado de la laptop | 100 % | 11/11 |
| ✅ | Qué se apaga en modo TIF: todo el homelab salvo Tailscale | 100 % | Lo hace el comando `tif` |
| ✅ | Parte 1: KVM/libvirt, Vagrant, Ansible, kubectl, UFW y prueba R12 | 100 % | 11/11: todo bien |
| 🟡 | Parte 2: usuario `tif`, comando `tif`, primer arranque del clúster y carga de las actas | 5 % | La está corriendo John. Antes del paso 5 va la limpieza de la VM de prueba |
| ⬜ | Parte 3: acceso de los compañeros por Tailscale y subida de resultados a GitHub | 0 % | Se escribe cuando ande el clúster. Incluye dejar que `tif` use el comando `tif` (regla de sudoers) |

## B. Código y herramientas: 85 %

| | Actividad | % | Nota |
|---|---|---|---|
| ✅ | Repositorio en GitHub (`Fonspem/TIF-SOD`) | 100 % | |
| 🟡 | Vagrantfile (libvirt principal, VirtualBox alternativa) | 85 % | Falta probarlo en la laptop |
| 🟡 | Ansible: base, disco de datos, etcd, k3s, node_exporter y módulo netem | 80 % | Falta correrlo contra las VM |
| 🟡 | Manifiesto de MinIO | 80 % | Falta desplegarlo |
| 🟡 | Servicio de metadatos con bloqueos, lease y fencing, con métricas y 7 pruebas | 95 % | Falta correrlo en el clúster |
| 🟡 | Monitoreo: Prometheus, Grafana con el tablero del Paso 5, node_exporter y la API en Docker | 90 % | Consultas probadas con un Prometheus local; falta verlo con MinIO real |
| 🟡 | Generador de actas, carga con SHA-256 y verificación | 95 % | Probado con un S3 simulado: 1.000 de 1.000 |
| 🟡 | Medición de elección de líder (E2) y clientes del bloqueo (E5) | 90 % | Falta correrlos en el clúster |
| 🟡 | Inyección de fallas E1, E3 y E4 | 80 % | Falta correrla en el clúster |
| 🟡 | Sonda de estado estable y análisis (tablas y figuras) | 90 % | Falta correrlos en el clúster |
| ✅ | Comando `tif` (prender, apagar y estado, con modo TIF) | 100 % | En la guía de la Parte 2; probado con comandos simulados |
| 🟡 | README probado desde cero | 70 % | Se prueba con la Parte 2 |

## C. Ejecución y mediciones: 0 %

| | Actividad | % | Nota |
|---|---|---|---|
| ⬜ | Paso 1: levantar las 4 VM y aprovisionarlas | 0 % | Parte 2 de la guía |
| ⬜ | Paso 2: etcd de 3 miembros, más E2 con 10 corridas por modo | 0 % | Se mide apenas etcd esté arriba |
| ⬜ | Paso 3: MinIO y rendimiento base | 0 % | Parte 2 de la guía |
| ⬜ | Paso 4: servicio de metadatos, demo con dos clientes y E5 | 0 % | |
| ⬜ | Paso 5: generar y cargar las 1.000 actas; tablero de Grafana | 0 % | Parte 2 de la guía |
| ⬜ | Paso 6: jornada de caos (E1, E3 y E4) con las sondas | 0 % | |
| ⬜ | Paso 7: verificación final de los 1.000 hashes | 0 % | |
| ⬜ | Capturas de evidencia (Grafana y terminal) | 0 % | Durante los pasos 1 a 7 |

## D. Informe (Google Doc): 65 %

| | Actividad | % | Nota |
|---|---|---|---|
| ✅ | Portada e índice | 100 % | El índice se actualiza al final; ya cambió el título del Anexo B |
| 🟡 | Resumen y palabras clave | 80 % | Faltan los resultados |
| ✅ | 1. Introducción y 2. Objetivos y escenario | 95 % | |
| ✅ | 3. Marco teórico (breve) | 95 % | Se sumaron tc netem e iptables (Hemminger, 2005) |
| ✅ | 4. Herramientas | 100 % | Con las decisiones 8 y 12: Docker en el anfitrión, sin Chaos Mesh, rendimiento con scripts propios |
| 🟡 | 5. Organización del equipo | 20 % | Faltan nombres, roles y autoevaluación |
| 🟡 | 6. Materiales y métodos | 85 % | La laptop con KVM ya es el entorno principal y el conjunto de datos está descrito. Falta el diagrama de arquitectura |
| 🟡 | 7. Implementación práctica | 75 % | Pasos 1, 3, 5 y 6 actualizados. Faltan las evidencias reales y acortar las líneas largas de los bloques de código de los pasos 2 a 4 y de E3, que se cortan en el PDF |
| 🟡 | 8. Resultados | 10 % | Tablas armadas, con 13 huecos [medir] |
| 🟡 | 9. Discusión y 10. Conclusiones | 40 % | Se completan con los datos |
| 🟡 | Referencias APA | 90 % | Revisar al final |
| ⬜ | Política de respaldo | 0 % | La pide el rol de almacenamiento |
| 🟡 | Runbook de la jornada de caos | 20 % | Hay un guion de 7 pasos; falta el documento |
| ⬜ | Post-mortem de cada experimento | 0 % | |
| ⬜ | Figuras: arquitectura y resultados de E1 a E5 | 0 % | `analyze.py` ya genera las de resultados |
| ⬜ | Anexo A: bitácoras | 0 % | |
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
1. laptop lista (Parte 1);
2. clúster arriba con las actas cargadas (Parte 2);
3. E2 y E5, que no necesitan nada más;
4. jornada de caos (E1, E3 y E4);
5. resultados en el informe;
6. defensa.

Mientras John prepara la laptop, el equipo:
- ✅ pasa al informe las decisiones 3, 8 y 12 (11/11);
- escribe la política de respaldo, el runbook y la plantilla de post-mortem;
- hace el diagrama de arquitectura.

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
