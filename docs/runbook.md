# Runbook de la jornada de caos

Guion de operación para correr los experimentos E1 a E5 de forma segura y repetible, y para respaldar y restaurar los datos. El [README](../README.md) explica cómo levantar el sistema; acá está cómo operarlo durante las pruebas. Cada experimento cierra con un post-mortem según la [plantilla](postmortem-plantilla.md).

**Quiénes.** La jornada se hace en pares, como pide el enunciado: una persona opera la terminal y la otra mira Grafana y lleva la bitácora. Se alternan entre experimentos.

**Dónde.** Todo se corre en el anfitrión, desde `scripts/`, con el entorno de Python activado:

```bash
cd scripts && . ../.venv/bin/activate
export MINIO_USER=admin MINIO_PASS='<contraseña>' KUBECONFIG=$PWD/../kubeconfig
SSH="ssh -F ../ansible/ssh_config"
```

Varios pasos usan dos terminales: una para la sonda y otra para la falla. En tmux, `Ctrl+b c` abre una ventana nueva y `Ctrl+b w` elige entre las abiertas.

**Forma recomendada: `chaos/jornada.sh`.** Corre E1, E3 y E4 de punta a punta con un solo comando y en una sola terminal: controla el estado estable (sección 2) y, si algo no está bien, no toca nada; prende las sondas, inyecta la falla, la revierte, espera a que el clúster vuelva a estar completo, corre `verify.py` y `analyze.py`, y guarda toda la salida en `results/evidencias/`. Si se corta en el medio (Ctrl+C o un error), revierte la falla y apaga las sondas igual. Los comandos de las secciones 5 a 7 quedan como referencia de lo que hace.

```bash
../chaos/jornada.sh estado     # sólo controles; no cambia nada
../chaos/jornada.sh e4         # unos 8 minutos
../chaos/jornada.sh e3         # unos 3 minutos
../chaos/jornada.sh e1-uno     # unos 5 minutos
../chaos/jornada.sh e1-dos     # unos 5 minutos
```

## 1. Reglas de la jornada

- **Una falla por vez.** No se inyecta la siguiente hasta que el sistema vuelva al estado estable (sección 2).
- **Radio de impacto acotado.** E1 apaga como máximo dos VM, vm4 y después vm3, y nunca vm1, que tiene el único servidor de k3s. E3 aísla solo a vm3. E4 dura 5 minutos.
- **Respaldo antes de empezar** (sección 8), para tener de dónde volver si algo sale mal.
- **Todo queda anotado.** Los scripts de `chaos/` y `leader_election.py` guardan la hora de cada falla en `results/eN_eventos.csv`. La bitácora suma lo que se hizo a mano y lo que se vio en Grafana, con la hora.
- **Grabar la pantalla** en los tramos que sirvan para el video: Grafana durante E1 y E2, la terminal en E3.

### Criterios para abortar

Si pasa alguna de estas cosas, se revierte la falla en curso, se anota la hora y se escribe el post-mortem aunque el experimento no haya terminado:

- `verify.py` informa un acta `CORRUPTO`, o con `ERROR` con los cuatro nodos arriba;
- una VM no vuelve a estar `running` 5 minutos después de encenderla;
- etcd queda sin líder más de 1 minuto fuera de E2 y E3;
- el anfitrión se queda sin memoria: en el panel «EXO: memoria disponible y swap usada», la swap crece sin parar.

## 2. Estado estable: controles antes de cada experimento

En Grafana, el tablero «TIF · Estado del sistema» abierto con los últimos 15 minutos: `http://<anfitrión>:3000/d/tif-estado`. En la terminal:

```bash
virsh -c qemu:///system list                       # tif_vm1 a tif_vm4 en running
kubectl get nodes                                  # 4 nodos Ready
kubectl -n minio get pods -o wide                  # 4 pods Running, uno por VM
curl -s -o /dev/null -w '%{http_code}\n' http://192.168.56.11:9000/minio/health/cluster   # 200: hay quórum de escritura
$SSH vm1 'etcdctl --endpoints=192.168.56.11:2379,192.168.56.12:2379,192.168.56.13:2379 endpoint status -w table'
                                                   # 3 miembros, uno con IS LEADER en true
curl -s -o /dev/null -w '%{http_code}\n' localhost:8000/health                             # 200
curl -s localhost:9090/api/v1/targets | jq -r '.data.activeTargets[].health' | sort | uniq -c   # todos "up"
python verify.py                                   # OK: 1000 / 1000
```

`verify.py` se corre antes del primer experimento y después de cada uno, para confirmar que la falla no dañó ninguna acta.

## 3. E2: caída del líder de etcd

- **Hipótesis:** aparece un líder nuevo en menos de 5 s y el servicio de metadatos se recupera solo.
- **Estado estable:** la sonda del servicio de metadatos responde sin errores.
- **Qué mirar:** «Líder actual de etcd», «etcd: cambios de líder (1 h)» y «API de metadatos: pedidos por segundo según código».

```bash
# Terminal 1: la sonda (cortarla con Ctrl+C cuando termine la terminal 2)
python probe.py meta --etiqueta e2-kill --intervalo 0.1 --salida ../results/e2_sonda_meta_kill.csv
# Terminal 2: 10 corridas con kill -9
python leader_election.py --modo kill --repeticiones 10 --salida ../results/e2_kill.csv

# Lo mismo con systemctl stop, con otra sonda
python probe.py meta --etiqueta e2-stop --intervalo 0.1 --salida ../results/e2_sonda_meta_stop.csv
python leader_election.py --modo stop --repeticiones 10 --salida ../results/e2_stop.csv
```

**Reversión:** el script vuelve a levantar cada miembro. Si alguno queda abajo: `$SSH vmN 'sudo systemctl start etcd'`.

## 4. E5: bloqueo huérfano (y la demostración del Paso 4)

- **Hipótesis:** al matar al dueño del bloqueo, su lease vence y otro cliente obtiene el bloqueo entre 10 y 15 s después (entre dos tercios del TTL de 15 s y el TTL completo).
- **Qué mirar:** «API de metadatos: pedidos por segundo según código», donde aparecen los 409.

```bash
python lock_clients.py concurrencia --clientes 2      # un 200 y un 409
python lock_clients.py huerfano --repeticiones 5 --salida ../results/e5_kill.csv
python lock_clients.py huerfano --ordenado --repeticiones 5 --salida ../results/e5_ordenado.csv
python lock_clients.py fencing                        # el dueño viejo recibe 409
```

**Reversión:** no hace falta. Un bloqueo trabado vence solo a los 15 s; para ver cuáles hay: `$SSH vm1 'etcdctl --endpoints=127.0.0.1:2379 get --prefix /locks/ --keys-only'`.

## 5. E1: caída de un nodo

- **Hipótesis:** con un nodo caído, las lecturas y las escrituras siguen sin pérdida; con dos, solo las lecturas.
- **Estado estable:** la sonda de MinIO lee y escribe sin errores.
- **Qué mirar:** «Nodos arriba: VM, etcd y MinIO», «MinIO: nodos y discos», «MinIO: pedidos y errores por segundo» y, cuando el nodo vuelve, «MinIO: objetos reparados (heal)».

```bash
# Terminal 1: la sonda (cortarla con Ctrl+C al final)
python probe.py s3 --etiqueta e1 --salida ../results/e1_sonda_s3.csv

# Terminal 2: un nodo
../chaos/e1_caida_nodo.sh apagar vm4        # observar 2 minutos
../chaos/e1_caida_nodo.sh encender vm4      # esperar el estado estable

# Terminal 2: dos nodos
../chaos/e1_caida_nodo.sh apagar vm4
../chaos/e1_caida_nodo.sh apagar vm3        # observar 2 minutos: las escrituras deberían fallar
../chaos/e1_caida_nodo.sh encender vm3
../chaos/e1_caida_nodo.sh encender vm4
```

**Cuidado:** una VM no debería quedar apagada más de 4 minutos. Pasados unos 5, Kubernetes marca para borrar el pod de MinIO de ese nodo; cuando la VM vuelve, el pod se recrea solo, pero la recuperación tarda más y se mezcla con la medición.

**Reversión:** `encender` y esperar a que la sección 2 dé todo bien, con 4 de 4 discos en «MinIO: nodos y discos».

## 6. E3: partición de red

- **Hipótesis:** la minoría (vm3) deja de aceptar escrituras y, al reunificar, no hay divergencia.
- **Qué mirar:** «Líder actual de etcd», «etcd: miembros con líder» y «MinIO: pedidos y errores por segundo».

```bash
# Una sonda por lado, contra etcd y contra MinIO, en segundo plano
python probe.py etcd --nodos 192.168.56.13:2379 --etiqueta e3-vm3 --salida ../results/e3_etcd_vm3.csv &
python probe.py etcd --nodos 192.168.56.11:2379 --etiqueta e3-vm1 --salida ../results/e3_etcd_vm1.csv &
python probe.py s3 --nodos http://192.168.56.13:9000 --etiqueta e3-vm3 --salida ../results/e3_s3_vm3.csv &
python probe.py s3 --nodos http://192.168.56.11:9000 --etiqueta e3-vm1 --salida ../results/e3_s3_vm1.csv &
../chaos/e3_particion.sh aislar vm3; sleep 60; ../chaos/e3_particion.sh revertir vm3; sleep 30; kill %1 %2 %3 %4

# Consistencia final: qué escrituras ve cada nodo después de reunificar
python probe.py etcd --comprobar ../results/e3_etcd_vm1.csv ../results/e3_etcd_vm3.csv
python probe.py s3 --comprobar ../results/e3_s3_vm1.csv ../results/e3_s3_vm3.csv
```

**Comprobar la reversión:** `$SSH vm3 'sudo iptables -S INPUT; sudo iptables -S OUTPUT' | grep 192.168.56` no tiene que mostrar nada. Si quedó alguna regla, se repite `../chaos/e3_particion.sh revertir vm3`.

**Nunca** `iptables -F`: borra también las reglas de k3s y deja al clúster sin red.

## 7. E4: red degradada

- **Hipótesis:** el sistema sigue funcionando, con más latencia.
- **Qué mirar:** «MinIO: latencia hasta el primer byte» y «API de metadatos: latencia».

```bash
python probe.py s3 --etiqueta e4 --salida ../results/e4_sonda_s3.csv &
../chaos/e4_netem.sh aplicar; sleep 300; ../chaos/e4_netem.sh revertir; sleep 60; kill %1
```

**Comprobar la reversión:** `for vm in vm1 vm2 vm3 vm4; do $SSH $vm 'tc qdisc show' | grep netem; done` no tiene que mostrar nada. `../chaos/e4_netem.sh revertir` se puede repetir sin problema.

## 8. Respaldo y restauración

Es la parte práctica de la política de respaldo del informe (sección 6.4). Las copias van a `respaldo/`, en la raíz del repositorio, que Git ignora: tienen las actas y no se suben.

### Antes de la jornada: instantánea de etcd y copia de las actas

```bash
./respaldo.sh etcd                          # instantánea de etcd en ../respaldo/etcd-AAAAMMDD-HHMM.db
cp ../results/manifest.csv ../respaldo/     # el manifiesto viaja con la copia
python verify.py --copia ../respaldo/actas  # verifica y copia en la misma pasada: OK: 1000 / 1000
```

`verify.py --copia` guarda solo las actas cuyo SHA-256 coincide con el manifiesto, así la copia nunca arrastra un acta dañada.

### Después de la jornada: prueba de restauración

Las dos pruebas restauran en lugares aparte y no tocan el clúster.

```bash
# Metadatos: restaura la instantánea en un etcd temporal de vm1 y cuenta las actas registradas
./respaldo.sh probar-etcd ../respaldo/etcd-AAAAMMDD-HHMM.db   # "Actas registradas en la instantánea: 1000"

# Contenido: sube la copia a un bucket nuevo y lo verifica contra el manifiesto original
time (MINIO_BUCKET=actas-restaurado python load.py --sin-api --carpeta ../respaldo/actas \
        --manifiesto ../results/manifest-restaurado.csv &&
      MINIO_BUCKET=actas-restaurado python verify.py)         # OK: 1000 / 1000
```

La restauración de etcd comprueba el hash de integridad de la instantánea; si el archivo está dañado, falla y lo dice. El tiempo que informa `time` es el tiempo de recuperación medido para 1.000 actas, y va al informe (sección 8.3).

## 9. Problemas frecuentes

| Síntoma | Qué hacer |
|---|---|
| Una VM figura `running` pero no contesta: ni ping ni ssh, y en Grafana está en rojo en las tres filas (falla gris) | `python caidas.py --vm vmN` dice desde cuándo. Con el watchdog, la VM se reinicia sola en menos de un minuto (en la prueba, 35 s); si no lo hace: `virsh -c qemu:///system screenshot tif_vmN ../results/evidencias/vmN-pantalla.png` (guarda la pantalla) y después `virsh -c qemu:///system reset tif_vmN`. Ver [el post-mortem del 12/11](postmortems/2026-11-12-vm3.md) |
| Una VM no arranca después de `encender` | `virsh -c qemu:///system start tif_vmN`; si no arranca, `cd ../vagrant && vagrant up vmN` |
| Un pod de MinIO no vuelve a `Running` | `kubectl -n minio describe pod minio-N` (los eventos están al final). Si quedó en `Terminating` con la VM ya arriba: `kubectl -n minio delete pod minio-N` y el StatefulSet lo recrea |
| Un miembro de etcd no vuelve | `$SSH vmN 'sudo systemctl start etcd; sudo journalctl -u etcd -n 30 --no-pager'` |
| La API de metadatos contesta 503 | No hay quórum de etcd: revisar el estado de etcd (sección 2) |
| Grafana no muestra datos de un nodo | `curl -s localhost:9090/api/v1/targets \| jq -r '.data.activeTargets[] \| select(.health != "up") \| .scrapeUrl + " " + .lastError'` |
| Quedaron reglas de E3 o la red lenta de E4 | La reversión de cada script se puede repetir (secciones 6 y 7) |
| El anfitrión se queda sin memoria | Ver el plan B de [docs/plan.md](plan.md) (menos RAM para vm2 a vm4) |

## 10. Después de la jornada

1. Verificación final (Paso 7): `python verify.py --salida ../results/verificacion_final.csv`.
2. Prueba de restauración (sección 8).
3. Tablas y figuras con `analyze.py` (README, «Tablas y figuras para el informe»).
4. Un post-mortem por experimento, copiando la [plantilla](postmortem-plantilla.md) a `docs/postmortems/eN.md`.
5. Subir al repositorio `results/` y `docs/postmortems/`.
