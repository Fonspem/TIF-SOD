# Capturas del 12/11/2026

Capturas del tablero de Grafana y de la consola de vm3, tomadas en la laptop del TIF. Las usa el
informe; ninguna muestra direcciones ni nombres de la red de la casa.

| Archivo | Qué muestra |
|---|---|
| `2026-11-12_0930_tablero-estado-barras-grises.png` | Primer tablero: las líneas de tiempo de estado salen grises (error de Grafana 13 con los mapeos de valores, arreglado con umbrales) |
| `2026-11-12_0938-0950_tablero-carga-actas.png` | Carga y verificación de las 1.000 actas (pedidos a MinIO y al servicio de metadatos) |
| `2026-11-12_1447_tablero-vm3-caida.png` | vm3 caída: etcd con 2 de 3 miembros y MinIO con 3 de 4 discos |
| `2026-11-12_1509_tablero-estado-8h-incidente.png` | Las 8 horas del día: vm3 en rojo desde las 11:28 en las filas de VM, etcd y MinIO |
| `2026-11-12_1509_tablero-recursos-8h-incidente.png` | A las 11:28 suben la CPU y la temperatura del anfitrión y quedan así: vm3 trabada |
| `2026-11-12_1527_vm3-pantalla-login.png` | Pantalla de vm3 congelada: solo el aviso de login, sin mensajes del núcleo |
| `2026-11-12_1553_tablero-vm3-recuperada.png` | vm3 de vuelta tras el reinicio forzado: etcd 3 de 3, MinIO 4 de 4 |
| `2026-11-12_1553_tablero-recursos-vm3-recuperada.png` | La CPU y la temperatura del anfitrión vuelven a sus valores normales |
| `2026-11-12_1618_tablero-reinicios-escalonados.png` | Las 4 VM reiniciadas de a una para agregarles el watchdog |
| `2026-11-12_1618_tablero-recursos-reinicios.png` | Recursos durante los reinicios escalonados |
| `2026-11-12_1640_tablero-prueba-panico.png` | Prueba con un pánico del núcleo en vm4: vuelve sola en 18 s |
| `2026-11-12_1640_tablero-recursos-prueba-panico.png` | Recursos durante la prueba del pánico |
| `2026-11-12_1647_tablero-prueba-watchdog.png` | Prueba del watchdog: vm4 congelada a propósito vuelve sola en 35 s |
| `2026-11-12_1647_tablero-recursos-prueba-watchdog.png` | Recursos durante la prueba del watchdog; MinIO repara 6 objetos |
| `2026-11-12_1659_tablero-e2-stop.png` | E2 con `systemctl stop`: el líder rota entre los tres miembros, sin errores en el servicio de metadatos |
| `2026-11-12_1659_tablero-recursos-e2-stop.png` | Recursos durante E2 con `systemctl stop` |
| `2026-11-12_2111_tablero-e5.png` | E5: el segundo cliente recibe 409 mientras espera el bloqueo (21:08 a 21:11); el líder de etcd no cambia |
| `2026-11-12_2111_tablero-recursos-e5.png` | Recursos durante E5 |
| `2026-11-12_2116_tablero-e5-y-restauracion.png` | E5 y, después, la prueba de restauración: la copia de las actas se sube a un bucket nuevo y se verifica (21:13 a 21:15) |
| `2026-11-12_2116_tablero-recursos-e5-y-restauracion.png` | Recursos durante E5 y la restauración: la CPU del anfitrión llega al 80 % |
| `2026-11-13_1447_tablero-e4.png` | E4, red degradada (14:40:57 a 14:46:00): la latencia de MinIO y de la API sube a cerca de 1 s (p95 de MinIO hasta 8 s) sin errores ni cambio de líder |
| `2026-11-13_1447_tablero-recursos-e4.png` | Recursos durante E4 |
| `2026-11-13_1452_tablero-e4-y-e3.png` | E4 y E3 (partición de vm3, 14:49:28 a 14:50:29): el p95 de MinIO llega a 10 s durante la partición; el líder sigue en vm1 |
| `2026-11-13_1452_tablero-recursos-e4-y-e3.png` | Recursos durante E4 y E3: al reunificar, MinIO repara unos 65 objetos |
| `2026-11-13_1530_tablero-e1-uno.png` | E1 con un nodo: vm4 apagada de golpe (15:24:40 a 15:27:11); en el primer minuto el p95 de MinIO llega a 10 s; el servicio de metadatos sigue sin errores y el líder de etcd, en vm1 |
| `2026-11-13_1530_tablero-recursos-e1-uno.png` | Recursos durante E1 con un nodo: con vm4 apagada, el anfitrión tiene 1,5 GB más libres; al volver vm4, MinIO repara unos 420 objetos |
| `2026-11-13_1537_tablero-e1-dos.png` | E1 con dos nodos: vm4 (15:32:32) y vm3 (15:32:52) apagadas hasta las 15:35:12; MinIO no responde (p50 y p95 de 10 s, sin errores 4xx ni 5xx), el servicio de metadatos sigue con 2 de 3 miembros de etcd y el líder sigue en vm1 |
| `2026-11-13_1538_tablero-recursos-e1-dos.png` | Recursos durante las dos partes de E1 (15:23 a 15:38) |
| `2026-11-12_0948_terminal-nodos-y-etcd.png` | Terminal después del primer arranque: `kubectl get nodes -o wide` con las 4 VM en `Ready` y `etcdctl endpoint status` con vm1 como líder (recortada) |
| `2026-11-12_1441_terminal-e2-aborta-vm3.png` | El intento de E2 aborta porque vm3 no responde (`'vm3': None`); la sonda del servicio de metadatos, sin errores (prompt tapado) |
| `2026-11-12_1547_terminal-teclado-vm3.png` | Prueba del teclado: después de un Enter con `virsh send-key`, la pantalla de vm3 no cambia (prompt y barra de tmux sacados) |
| `2026-11-12_1659_terminal-e2-stop.png` | Salida de E2 con `systemctl stop`: 10 corridas, medianas de 62 y 78 ms y la sonda sin errores (prompt tapado) |
