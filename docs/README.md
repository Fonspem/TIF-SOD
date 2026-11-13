# Documentación

| Archivo o carpeta | Qué es | Cuándo leerlo |
|---|---|---|
| [`runbook.md`](runbook.md) | Guion de operación de la jornada de caos: controles previos, criterios para abortar, cómo revertir cada falla, respaldo y restauración | Antes de correr un experimento |
| [`postmortems/`](postmortems/) | Un informe por experimento (E1 a E5) y uno por el incidente de vm3: hipótesis, cronología, impacto medido, análisis y acciones | Para entender qué pasó en cada prueba |
| [`postmortem-plantilla.md`](postmortem-plantilla.md) | La plantilla de esos informes | Al escribir uno nuevo |
| [`capturas/`](capturas/) | Capturas de Grafana y de la terminal, con la fecha y la hora en el nombre; su [README](capturas/README.md) dice qué muestra cada una y en qué figura del informe está | Para ver la evidencia visual |
| [`figuras/`](figuras/) | Figuras propias del informe (arquitectura y gráficos) y el código que las genera | Para regenerarlas |
| [`versiones.md`](versiones.md) | Versiones exactas de cada componente, del anfitrión y de las VM | Para reproducir el entorno |
| [`plan.md`](plan.md) | Plan de trabajo y estado de cada actividad, con porcentajes | Para saber qué falta |

## Post-mortems

| Archivo | Qué | Resultado |
|---|---|---|
| [`2026-11-12-e2.md`](postmortems/2026-11-12-e2.md) | E2 · caída del líder de etcd | Confirmada |
| [`2026-11-12-e5.md`](postmortems/2026-11-12-e5.md) | E5 · bloqueo huérfano y *fencing* | Confirmada |
| [`2026-11-12-vm3.md`](postmortems/2026-11-12-vm3.md) | Incidente no planificado: vm3 congelada | Resuelto con un *watchdog* |
| [`2026-11-13-e4.md`](postmortems/2026-11-13-e4.md) | E4 · red degradada | Confirmada |
| [`2026-11-13-e3.md`](postmortems/2026-11-13-e3.md) | E3 · partición | Confirmada en etcd; en MinIO, en parte |
| [`2026-11-13-e1.md`](postmortems/2026-11-13-e1.md) | E1 · caída de uno y de dos nodos | Con un nodo, confirmada; con dos, en parte |
