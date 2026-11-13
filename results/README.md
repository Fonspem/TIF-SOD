# Resultados

Datos crudos de las corridas del 12 y el 13/11/2026 en la laptop del TIF. Las tablas y los números del informe salen de acá (con `scripts/analyze.py`), y cada experimento tiene su post-mortem en [`docs/postmortems/`](../docs/postmortems/). Las horas son de Argentina (UTC−3); los CSV guardan el tiempo como *epoch* en segundos.

## Formatos

| Archivo | Columnas |
|---|---|
| Sondas (`*_sonda_*.csv`, `e3_etcd_*.csv`, `e3_s3_*.csv`) | `t` (epoch), `objetivo` (`meta`, `s3` o `etcd`), `etiqueta`, `nodo` que respondió, `op` (`lectura` o `escritura`), `ok` (1 o 0), `ms`, `clave`, `error`. Una fila por pedido; la sonda hace una lectura y una escritura cada 0,5 s |
| Eventos (`eN_eventos.csv`, `watchdog_eventos.csv`) | epoch, evento (`apagar`, `encender`, `detener`, `iniciar`, `aislar`, …) y VM. `analyze.py` los usa para partir las sondas en tramos |
| Elecciones (`e2_kill.csv`, `e2_stop.csv`) | `corrida`, `modo`, `lider_caido`, `lider_nuevo`, `t_lider_ms` (hasta el nuevo líder), `t_escritura_ms` (hasta la primera escritura confirmada) |
| Bloqueos (`e5_kill.csv`, `e5_ordenado.csv`) | `corrida`, `modo`, `ttl_s`, `t_liberacion_s` (hasta que otro cliente obtiene el bloqueo) |
| Manifiestos (`manifest*.csv`) | `key`, `sha256`, `bytes`: lo que se subió y su hash |
| Verificaciones (`verificacion_*.csv`) | `key`, `resultado` (`OK` o la falla), `detalle` |

## Por experimento

| Experimento | Datos | Salidas de la terminal (`evidencias/`) | Figuras (`figuras/`) |
|---|---|---|---|
| Carga inicial (12/11) | `manifest.csv`, `verificacion_inicial.csv` | `paso9-generar.txt`, `paso9-carga.txt`, `paso9-verificacion.txt` | — |
| E2 · caída del líder de etcd (12/11) | `e2_kill.csv`, `e2_stop.csv`, `e2_eventos.csv`, `e2_sonda_meta_kill.csv`, `e2_sonda_meta_stop.csv` | `e2-antes-etcd.txt`, `e2-kill.txt`, `e2-stop.txt`, `e2-sonda-kill.txt`, `e2-sonda-stop.txt`, `e2-tabla.txt` | `e2.png`, `e2_meta_kill.png`, `e2_meta_stop.png` |
| E5 · bloqueo huérfano y *fencing* (12/11) | `e5_kill.csv`, `e5_ordenado.csv` | `e5-concurrencia.txt`, `e5-huerfano-kill.txt`, `e5-huerfano-ordenado.txt`, `e5-fencing.txt`, `e5-tabla.txt` | `e5.png` |
| Incidente de vm3 (12/11) | — | `incidente-vm3-*.txt` y `incidente-vm3-pantalla*.png`, `verificacion-post-incidente.txt` | — |
| *Watchdog* (12/11) | `watchdog_eventos.csv` | `watchdog-ansible.txt`, `watchdog-vms.txt`, `prueba-panico.txt`, `prueba-watchdog.txt` | — |
| Respaldo y restauración (12/11) | `manifest-restaurado.csv` | `respaldo-actas.txt`, `respaldo-etcd.txt`, `restauracion-actas.txt`, `restauracion-etcd.txt` | — |
| Estado estable antes y después de cada parte de la jornada (13/11) | — | `caos-estado-1437.txt`, `-1521`, `-1522`, `-1538`; `caos-respaldo-etcd.txt` | — |
| E4 · red degradada (13/11, 14:39) | `e4_sonda_s3_1439.csv`, `e4_sonda_meta_1439.csv`, `e4_eventos.csv`, `manifest-e4-antes.csv`, `manifest-e4-durante.csv` | `caos-e4-1439.txt` (corrida), `caos-e4-1439-analisis.txt` (reanálisis), `caos-e4-1439-sonda-*.txt` | `e4-1439.png` |
| E3 · partición (13/11, 14:48) | `e3_etcd_vm1_1448.csv`, `e3_etcd_vm3_1448.csv`, `e3_s3_vm1_1448.csv`, `e3_s3_vm3_1448.csv`, `e3_eventos.csv` | `caos-e3-1448.txt`, `caos-e3-1448-sonda-*.txt` | `e3-etcd-1448.png`, `e3-s3-1448.png` |
| E1 · un nodo (13/11, 15:23) | `e1_uno_sonda_s3_1523.csv`, `e1_uno_sonda_meta_1523.csv`, `e1_eventos.csv`, `manifest-e1-antes.csv`, `manifest-e1-uno.csv` | `caos-e1-uno-1523.txt`, `caos-e1-uno-1523-sonda-*.txt` | `e1-uno-1523.png` |
| E1 · dos nodos (13/11, 15:31) | `e1_dos_sonda_s3_1531.csv`, `e1_dos_sonda_meta_1531.csv`, `e1_eventos.csv` | `caos-e1-dos-1531.txt`, `caos-e1-dos-1531-sonda-*.txt` | `e1-dos-1531.png` |
| Verificación final (13/11, 15:38) | `verificacion_final.csv` | `paso7-verificacion-final.txt` | — |

Los archivos `paso6-*`, `paso7-minio.txt`, `paso8-*` y `paso9-*` son del primer arranque del clúster (12/11): toman el nombre de los pasos de la guía de instalación del servidor, no de los pasos del informe.

## Reglas

- Cada corrida de `chaos/jornada.sh` lleva la hora de inicio en el nombre, así dos corridas no se pisan. Los archivos de eventos (`eN_eventos.csv`) se van agregando: una corrida nueva suma filas.
- Antes de subir resultados nuevos se revisa que no tengan datos privados de la red del anfitrión: solo pueden aparecer las direcciones de las VM (192.168.56.x y 192.168.121.x) y las internas de Kubernetes.
- `dataset/` (las actas generadas) y `respaldo/` no se suben: se regeneran con `scripts/generar_actas.py` (semilla fija) y `scripts/respaldo.sh`.
