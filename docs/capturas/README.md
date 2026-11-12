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
