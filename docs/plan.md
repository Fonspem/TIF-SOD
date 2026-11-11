# Plan del TIF: estado y orden de trabajo

Actualizado: 11 de noviembre de 2026.

Referencias: ✅ terminado · 🟡 en curso, con su porcentaje · ⬜ sin empezar · ⛔ trabado (la nota dice por qué)

## Dónde estamos

- **Avance general: alrededor del 30 %.** Es una estimación a ojo para ubicarnos, ponderada por área según la tabla de abajo.
- **Ya está hecho:**
  - Casi todo el código y las herramientas de medición, probados en local.
  - El borrador del informe completo, salvo los resultados.
- **Falta:**
  - Preparar el servidor y correr todo en el clúster.
  - Completar los resultados en el informe.
  - Armar los entregables de la defensa.
- **El cuello de botella es la laptop EXO.** Casi todo lo que falta depende de ella. Lo que no depende, lo adelanta el equipo en paralelo.

| Área | Avance | Peso en el total |
|---|---|---|
| A. Servidor (laptop EXO) | 5 % | 10 % |
| B. Código y herramientas | 65 % | 25 % |
| C. Ejecución y mediciones | 0 % | 25 % |
| D. Informe | 55 % | 25 % |
| E. Defensa y entregables | 0 % | 15 % |
| **Total** | **≈ 30 %** | |

## Decisiones pendientes

| # | Qué hay que decidir | Recomendación | Qué destraba |
|---|---|---|---|
| 3 | Formato de los 1.000 documentos | Actas de examen ficticias, la mayoría en PDF y el resto en .txt, de pocos KB a unos 5 MB, con semilla fija para que salgan siempre iguales | Generador y carga (Paso 5), E1 y la verificación final |
| 8 | Dónde corren Prometheus y Grafana, y si se usa Chaos Mesh | En la laptop, con Docker, como ya prevén los requisitos del servidor. Chaos Mesh queda sólo nombrado en el marco teórico | Tablero de Grafana, docker-compose y la demo |
| 12 | Variante principal del informe | La laptop con KVM pasa a ser la principal, porque ahí se mide. VirtualBox queda como alternativa | Texto de 6.1, Paso 1 y Anexo B |

## A. Servidor (laptop EXO): 5 %

| | Actividad | % | Nota |
|---|---|---|---|
| ⬜ | Relevar el estado actual de la laptop con el bloque de la sección 9 de `requisitos-servidor.md` | 0 % | Primer paso |
| ⬜ | Decidir qué se apaga o se deshabilita de lo que ya corre en la laptop | 0 % | Hace falta el contexto de Red Laboratorio |
| 🟡 | Requisitos R1 a R11: modo texto, energía, red, SSH, KVM/libvirt, convivencia con Docker, Vagrant, disco, memoria, Docker y herramientas | 10 % | Debian y Docker ya están |
| ⬜ | Prueba de aceptación R12: una VM de prueba con red, apagado brusco, corte de enlace y snapshot | 0 % | Con esto, el servidor queda listo |

## B. Código y herramientas: 65 %

| | Actividad | % | Nota |
|---|---|---|---|
| ✅ | Repositorio en GitHub (`Fonspem/TIF-SOD`) | 100 % | Subido el 11/11 |
| 🟡 | Vagrantfile (VirtualBox y libvirt) | 85 % | Falta probarlo en la laptop |
| 🟡 | Ansible: base, disco de datos, etcd y k3s | 80 % | Falta correrlo contra las VM |
| 🟡 | Manifiesto de MinIO (`k8s/minio.yaml`) | 80 % | Falta desplegarlo |
| 🟡 | Servicio de metadatos con bloqueos, lease y fencing, con 7 pruebas | 95 % | Usa el puerto 8000, como piden los requisitos del servidor |
| 🟡 | Medición de la elección de líder (E2) | 90 % | Falta correrla en el clúster |
| 🟡 | Clientes del bloqueo: concurrencia, bloqueo huérfano (E5) y fencing | 90 % | Falta correrlos en el clúster |
| 🟡 | Inyección de fallas E1, E3 y E4 (`chaos/`) | 80 % | Falta correrla en el clúster |
| 🟡 | Sonda de estado estable y análisis (tablas y figuras) | 90 % | Falta correrlos en el clúster |
| 🟡 | Verificación de hashes (`verify.py`) | 90 % | Falta correrla en el clúster |
| ⛔ | Generador de las 1.000 actas y script de carga con manifiesto SHA-256 | 10 % | Espera la decisión 3. El borrador del informe tiene una versión vieja |
| ⛔ | Monitoreo: docker-compose de Prometheus y Grafana, node_exporter en las VM y tablero del Paso 5 | 0 % | Espera la decisión 8 |
| ⬜ | Instalación en el host de etcdctl, mc y warp, con versiones fijas | 0 % | Los requisitos del servidor dicen que los pone el repo |
| 🟡 | README probado desde cero | 70 % | Se prueba en la etapa 2 |

## C. Ejecución y mediciones: 0 %

| | Actividad | % | Nota |
|---|---|---|---|
| ⬜ | Paso 1: levantar las 4 VM y aprovisionarlas con Ansible | 0 % | Necesita el servidor listo |
| ⬜ | Paso 2: etcd de 3 miembros, más E2 con 10 corridas por modo | 0 % | No necesita MinIO: se mide apenas etcd esté arriba |
| ⬜ | Paso 3: MinIO, bucket y rendimiento base con warp | 0 % | |
| ⬜ | Paso 4: servicio de metadatos, demo con dos clientes y E5 | 0 % | |
| ⛔ | Paso 5: generar y cargar las 1.000 actas; tablero de Grafana | 0 % | Decisiones 3 y 8 |
| ⬜ | Paso 6: jornada de caos (E1, E3 y E4) con las sondas | 0 % | Después del Paso 5 |
| ⬜ | Paso 7: verificación final de los 1.000 hashes | 0 % | |
| ⬜ | Capturas de evidencia (Grafana y terminal) | 0 % | Durante los pasos 1 a 7 |

## D. Informe (Google Doc): 55 %

| | Actividad | % | Nota |
|---|---|---|---|
| ✅ | Portada | 100 % | Es la de ustedes; no se toca |
| ✅ | Índice | 100 % | Ya está insertado; se actualiza al final |
| 🟡 | Resumen y palabras clave | 80 % | Faltan los resultados |
| ✅ | 1. Introducción y 2. Objetivos y escenario | 95 % | |
| ✅ | 3. Marco teórico (breve) y 4. Herramientas | 90 % | |
| 🟡 | 5. Organización del equipo | 20 % | Faltan nombres, roles y autoevaluación |
| 🟡 | 6. Materiales y métodos | 70 % | Falta el diagrama de arquitectura como figura. 6.2 depende de la decisión 3; el entorno, de la 12 |
| 🟡 | 7. Implementación práctica | 65 % | Faltan las evidencias reales. El Paso 5 depende de la decisión 3 |
| 🟡 | 8. Resultados | 10 % | Las tablas están armadas, con 13 huecos [medir] |
| 🟡 | 9. Discusión y 10. Conclusiones | 40 % | Se completan con los datos |
| 🟡 | Referencias APA | 90 % | Al final, revisar que estén todas las citadas |
| ⬜ | Política de respaldo | 0 % | La pide el rol de almacenamiento y todavía no está |
| 🟡 | Runbook: guion de operación de la jornada de caos | 20 % | Hay un guion de 7 pasos; falta el documento |
| ⬜ | Post-mortem de cada experimento | 0 % | La plantilla se puede dejar lista ahora |
| ⬜ | Figuras: arquitectura y resultados de E1 a E5 | 0 % | `analyze.py` ya genera las de resultados |
| ⬜ | Anexo A: bitácoras | 0 % | |
| ✅ | Anexo B: variante de la laptop | 100 % | Cambia si la laptop pasa a ser la principal (decisión 12) |
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

El camino crítico es:

1. laptop lista;
2. VM y etcd;
3. MinIO;
4. carga de las actas;
5. jornada de caos;
6. resultados;
7. informe y defensa.

Todo lo demás va en paralelo, para que nadie quede esperando.

**Etapa 1, ahora**
- **Usuario:**
  - Prepara la laptop (R1 a R12) y trae el relevamiento.
  - Contesta las decisiones 3, 8 y 12.
- **el equipo, en paralelo:**
  - Generador de actas y carga (cuando esté la decisión 3).
  - docker-compose de monitoreo y tablero (cuando esté la decisión 8).
  - Instalación de etcdctl, mc y warp.
  - Política de respaldo, runbook y plantilla de post-mortem.
  - Diagrama de arquitectura.

**Etapa 2, con la laptop lista**
- Pasos 1 y 2: VM, Ansible y etcd. E2 se mide apenas etcd esté arriba.
- Paso 3: MinIO y warp.
- Paso 4: servicio de metadatos, demo y E5.

**Etapa 3**
- Paso 5: actas y tablero.
- Paso 6: jornada de caos con sus post-mortems.
- Paso 7: verificación final.
- Capturas en cada paso y tramos grabados para el video.

**Etapa 4**
- **el equipo:** informe con resultados y figuras.
- **Usuario:** nombres, autoevaluación y bitácoras.
- Presentación, video y ensayo de la demo.

## Notas de las pruebas locales (para la discusión)

- **Escrituras ambiguas.** En la partición simulada, algunas escrituras se aplicaron igual al reunificar aunque el cliente las dio por fallidas por tiempo agotado. Habían quedado en los búferes de TCP y llegaron al líder después.
  - No hubo divergencia: todos los miembros ven lo mismo.
  - Pero un error en el cliente no garantiza que la operación no haya ocurrido.
  - Por eso el servicio de metadatos usa transacciones con comparación: reintentar no rompe nada.
- **Caída del líder y servicio de metadatos.** Con `kill -9` al líder, el servicio no devolvió errores (con un tiempo de espera de 8 s en el cliente). Algunas escrituras tardaron unos 2 s: el primer miembro consultado no respondió dentro de `ETCD_TIMEOUT` y el servicio pasó al siguiente.
- **Minoría aislada.** El miembro aislado rechaza escrituras y lecturas linealizables durante toda la partición. La mayoría sólo tiene uno o dos segundos de errores, si tiene que elegir un líder nuevo.
