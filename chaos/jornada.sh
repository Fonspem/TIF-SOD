#!/usr/bin/env bash
# Jornada de caos: corre E1, E3 o E4 de punta a punta, con sus sondas, y revierte la falla aunque
# algo salga mal o se corte con Ctrl+C. Sigue docs/runbook.md (secciones 2, 5, 6 y 7).
#
# Uso, en el anfitrión, con el entorno del TIF (venv, MINIO_USER y MINIO_PASS, KUBECONFIG):
#   chaos/jornada.sh estado    controles de estado estable; no cambia nada
#   chaos/jornada.sh e4        red degradada: 5 min de netem (200 ms y 5 % de pérdida) en las 4 VM
#   chaos/jornada.sh e3        partición: vm3 aislada de las otras tres VM durante 60 s
#   chaos/jornada.sh e1-uno    caída de un nodo: vm4 apagada de golpe durante 150 s
#   chaos/jornada.sh e1-dos    caída de dos nodos: vm4 y vm3 apagadas de golpe; vuelve vm3 y después vm4
#
# Cada experimento:
#   1. controla el estado estable y, si algo no está bien, no toca nada;
#   2. prende las sondas (probe.py) y deja un tramo «antes»;
#   3. inyecta la falla con los scripts de chaos/ y mide mientras dura;
#   4. la revierte, espera a que el clúster vuelva a estar completo y anota cuánto tardó;
#   5. apaga las sondas, corre verify.py y analyze.py.
# Si se corta en el medio (Ctrl+C o un error), revierte la falla y apaga las sondas igual.
#
# Los CSV quedan en results/ con la hora de inicio en el nombre (no se mezclan con otra corrida),
# las figuras en results/figuras/ y toda la salida en results/evidencias/caos-<experimento>-<hora>.txt.
# Las duraciones se pueden cambiar con variables de entorno (T_ANTES, T_FALLA, T_DESPUES, T_PAUSA), por
# ejemplo para probar el script; los valores por defecto son los del runbook.
set -uo pipefail   # sin -e a propósito: la reversión tiene que correr aunque falle un paso
trap '' PIPE       # si se cierra la terminal o el tee, que la reversión no muera por SIGPIPE

cd "$(dirname "$0")/../scripts" || exit 1
RES=../results
EV=$RES/evidencias
SSH=(ssh -F "${SSH_CONFIG:-../ansible/ssh_config}" -o ConnectTimeout=5 -o LogLevel=ERROR)
VIRSH=(virsh -c qemu:///system)
ETCD=192.168.56.11:2379,192.168.56.12:2379,192.168.56.13:2379
IPS=(192.168.56.11 192.168.56.12 192.168.56.13 192.168.56.14)
VMS=(vm1 vm2 vm3 vm4)
MUESTRA=${MUESTRA:-20}            # actas de la muestra de rendimiento (escritura y lectura)
T_PAUSA=${T_PAUSA:-20}            # pausa entre pasos (por ejemplo, después de inyectar la falla)
DATASET=../dataset/actas
HORA=$(date +%H%M)
exp=${1:-}

case "$exp" in
  estado | e4 | e3 | e1-uno | e1-dos) ;;
  *) echo "uso: $0 estado | e4 | e3 | e1-uno | e1-dos" >&2; exit 2 ;;
esac

mkdir -p "$EV" "$RES/figuras"
[ -e "$EV/caos-$exp-$HORA.txt" ] && HORA=$(date +%H%M%S)   # otra corrida en el mismo minuto
LOG=$EV/caos-$exp-$HORA.txt
# Toda la salida va también al archivo de evidencias. El tee ignora Ctrl+C, así sigue anotando
# mientras se revierte la falla.
exec > >(trap '' INT TERM; exec tee -a "$LOG") 2>&1
TEE=$!

log() { printf '%s %s\n' "$(date +%H:%M:%S)" "$*"; }

# ------------------------------------------------------------------ estado estable

# Clúster completo: 3 miembros de etcd sanos, 4 nodos Ready y MinIO listo en las 4 VM.
# etcd y MinIO se consultan directo: el estado de los pods en Kubernetes tarda en actualizarse.
completo() {
  local ip
  [ "$("${SSH[@]}" vm1 "etcdctl --endpoints=$ETCD endpoint health" 2>&1 | grep -c 'is healthy')" -eq 3 ] || return 1
  [ "$(kubectl get nodes --no-headers 2>/dev/null | awk '$2 == "Ready"' | wc -l)" -eq 4 ] || return 1
  for ip in "${IPS[@]}"; do
    curl -sf -m 3 -o /dev/null "http://$ip:9000/minio/health/ready" || return 1
  done
}

# Restos de un experimento anterior: netem en alguna VM o reglas de E3 en alguna VM
restos() {
  local vm n=0 r
  for vm in "${VMS[@]}"; do
    r=$("${SSH[@]}" "$vm" 'tc qdisc show; sudo iptables -S INPUT; sudo iptables -S OUTPUT' 2>/dev/null) || { echo "$vm: sin respuesta"; n=1; continue; }
    if grep -q netem <<<"$r"; then echo "$vm: netem activo"; n=1; fi
    if grep -Eq -- '-[sd] 192\.168\.56\.1[1-4]/32 -j DROP' <<<"$r"; then echo "$vm: reglas de E3"; n=1; fi
  done
  return $n
}

si() { if "$@" >/dev/null 2>&1; then echo "✓"; else echo "✗"; fi; }

cuenta() {  # cuenta <obtenido> <esperado> <qué>: ✓ o ✗; marca «bien» de controles() si no da
  if [ "$1" -eq "$2" ]; then echo "  ✓ $3: $1 de $2"; else echo "  ✗ $3: $1 de $2"; bien=1; fi
}

controles() {
  local bien=0 n r ip
  log "Controles de estado estable"
  cuenta "$("${VIRSH[@]}" list --name --state-running 2>/dev/null | grep -c '^tif_vm[1-4]$')" 4 "VMs en running"
  cuenta "$(kubectl get nodes --no-headers 2>/dev/null | awk '$2 == "Ready"' | wc -l)" 4 "nodos Ready"
  cuenta "$(kubectl -n minio get pods --no-headers 2>/dev/null | awk '$3 == "Running"' | wc -l)" 4 "pods de MinIO en Running"
  cuenta "$("${SSH[@]}" vm1 "etcdctl --endpoints=$ETCD endpoint health" 2>&1 | grep -c 'is healthy')" 3 "miembros de etcd sanos"
  n=0
  for ip in "${IPS[@]}"; do curl -sf -m 3 -o /dev/null "http://$ip:9000/minio/health/ready" && n=$((n + 1)); done
  cuenta "$n" 4 "VMs con MinIO listo"
  r=$(si curl -sf -m 3 -o /dev/null "http://${IPS[0]}:9000/minio/health/cluster"); [ "$r" = "✓" ] || bien=1
  echo "  $r MinIO con quórum de escritura"
  r=$(si curl -sf -m 5 -o /dev/null localhost:8000/health); [ "$r" = "✓" ] || bien=1
  echo "  $r servicio de metadatos (/health)"
  if r=$(restos); then echo "  ✓ sin restos de experimentos anteriores (netem, reglas de E3)"
  else echo "  ✗ quedan restos:"; echo "      ${r//$'\n'/$'\n'      }"; bien=1; fi
  if [ -d "$DATASET" ]; then echo "  ✓ actas originales en dataset/ (para la muestra de rendimiento)"
  else echo "  ⚠️ no está $DATASET: se saltea la muestra de rendimiento"; fi
  r=$(curl -s -m 5 localhost:9090/api/v1/targets)
  echo "  · objetivos de Prometheus: $(grep -o '"health":"up"' <<<"$r" | wc -l) up de $(grep -o '"health":"[a-z]*"' <<<"$r" | wc -l)"
  echo "  · memoria del anfitrión: $(free -m | awk '/^Mem:/ {print $7 " MB disponibles"} /^Swap:/ {print ", swap usada " $3 " MB"}' | paste -sd '' -)"
  return $bien
}

# ------------------------------------------------------------------ sondas, muestras y eventos

SONDAS=()
sonda() {  # sonda <objetivo> <etiqueta> <csv> [opciones de probe.py]
  local objetivo=$1 etiqueta=$2 csv=$3
  shift 3
  python -u probe.py "$objetivo" --etiqueta "$etiqueta" --informe 0 --salida "$csv" "$@" \
    > "$EV/caos-$exp-$HORA-sonda-$etiqueta-$objetivo.txt" 2>&1 &
  SONDAS+=("$!")
  log "sonda $objetivo ($etiqueta) en marcha → ${csv#../}"
}

parar_sondas() {
  local pid f
  [ ${#SONDAS[@]} -gt 0 ] || return 0
  log "apago las sondas"
  for pid in "${SONDAS[@]}"; do kill -TERM "$pid" 2>/dev/null; done
  for pid in "${SONDAS[@]}"; do wait "$pid" 2>/dev/null; done
  SONDAS=()
  for f in "$EV/caos-$exp-$HORA-sonda-"*.txt; do
    [ -f "$f" ] && { echo "--- ${f##*/}"; sed -n '/^Resumen/,$p' "$f"; }
  done
}

evento() {  # anota un evento propio (por ejemplo «completo») en el CSV de eventos del experimento
  printf '%s,%s\n' "$(date +%s.%N)" "$1" >> "$EVENTOS"
}

# Muestra de rendimiento: sube MUESTRA actas a un bucket aparte y las vuelve a leer.
muestra() {  # muestra <bucket> <segundos máximos para subir> <segundos máximos para leer>
  local bucket=$1 man=$RES/manifest-$1.csv dir=/tmp/tif-muestra-$MUESTRA
  [ -d "$DATASET" ] || { log "muestra $bucket: salteada (no está $DATASET)"; return 0; }
  if [ ! -d "$dir" ]; then
    mkdir -p "$dir" &&
      find "$(cd "$DATASET" && pwd)" -maxdepth 1 -type f | sort | head -n "$MUESTRA" | xargs -r ln -sf -t "$dir"
  fi
  rm -f "$man"
  log "muestra $bucket: subo $MUESTRA actas (máx. $2 s)"
  MINIO_BUCKET=$bucket timeout --foreground "$2" python -u load.py --sin-api --carpeta "$dir" --manifiesto "$man" 2>&1 |
    tail -n 4
  [ "${PIPESTATUS[0]}" -eq 124 ] && log "muestra $bucket: la subida no terminó en $2 s"
  [ -f "$man" ] || return 0
  log "muestra $bucket: leo y verifico (máx. $3 s)"
  MINIO_BUCKET=$bucket timeout --foreground "$3" python -u verify.py --manifiesto "$man" 2>&1 | tail -n 4
  [ "${PIPESTATUS[0]}" -eq 124 ] && log "muestra $bucket: la lectura no terminó en $3 s"
  return 0
}

esperar_hasta() {  # esperar_hasta <t0> <segundos>: duerme hasta t0 + segundos
  local resto=$(($1 + $2 - $(date +%s)))
  [ "$resto" -gt 0 ] && sleep "$resto"
  return 0
}

esperar_completo() {  # esperar_completo <t0>: hasta 10 min; anota el evento «completo»
  local t0=$1
  log "espero a que el clúster esté completo (etcd 3 de 3, 4 nodos Ready y MinIO listo en las 4 VM)…"
  until completo; do
    if [ $(($(date +%s) - t0)) -ge 600 ]; then
      log "✗ el clúster no se completó en 10 minutos: frená y mandá esta salida"
      return 1
    fi
    sleep 5
  done
  evento completo
  log "✓ clúster completo, $(($(date +%s) - t0)) s después de revertir la falla"
}

# ------------------------------------------------------------------ reversión

FALLA=""      # lo que hay que revertir si se corta: netem | particion | vm (con APAGADAS)
APAGADAS=()

revertir() {
  local vm i
  case "$FALLA" in
    netem)
      ../chaos/e4_netem.sh revertir
      for i in 1 2 3; do restos >/dev/null && break; sleep 2; ../chaos/e4_netem.sh revertir; done ;;
    particion)
      ../chaos/e3_particion.sh revertir vm3
      for i in 1 2 3; do restos >/dev/null && break; sleep 2; ../chaos/e3_particion.sh revertir vm3; done ;;
    vm)
      for ((i = ${#APAGADAS[@]} - 1; i >= 0; i--)); do
        vm=${APAGADAS[i]}
        "${VIRSH[@]}" domstate "tif_$vm" 2>/dev/null | grep -q running || ../chaos/e1_caida_nodo.sh encender "$vm"
      done
      APAGADAS=() ;;
  esac
  FALLA=""
}

al_salir() {
  local rc=$?
  trap - EXIT INT TERM
  if [ -n "$FALLA" ] || [ ${#SONDAS[@]} -gt 0 ]; then
    log "⚠️ corte antes de terminar: revierto la falla y apago las sondas"
    revertir
    parar_sondas
    log "falla revertida. Antes de seguir: chaos/jornada.sh estado"
  fi
  log "salida guardada en ${LOG#../}"
  exec 1>&- 2>&-
  wait "$TEE" 2>/dev/null
  exit "$rc"
}
trap al_salir EXIT
trap 'exit 130' INT TERM

# ------------------------------------------------------------------ experimentos

empezar() {  # empezar <archivo de eventos>: controles; si no da bien, no se toca nada
  EVENTOS=$1
  export EVENTOS
  log "Experimento $exp (salida en ${LOG#../})"
  if ! controles; then
    log "✗ el sistema no está en estado estable: no se inyecta nada. Frená y mandá esta salida."
    exit 1
  fi
  log "✓ estado estable"
}

verificar() {  # apaga las sondas y comprueba que las 1.000 actas sigan bien
  parar_sondas
  log "verify.py: ¿las 1.000 actas siguen bien?"
  python -u verify.py 2>&1 | tail -n 6
}

analizar() {  # analizar <nombre de la figura> <csv...>: tablas y figura de analyze.py
  local fig=$RES/figuras/$1-$HORA.png
  shift
  log "analyze.py: ${*#../}"
  python analyze.py sonda "$@" --eventos "$EVENTOS" --figura "$fig"
}

e4() {
  local t0 tf
  T_ANTES=${T_ANTES:-60} T_FALLA=${T_FALLA:-300} T_DESPUES=${T_DESPUES:-60}
  empezar "$RES/e4_eventos.csv"
  t0=$(date +%s)
  sonda s3 e4 "$RES/e4_sonda_s3_$HORA.csv"
  sonda meta e4 "$RES/e4_sonda_meta_$HORA.csv"
  sleep "$T_PAUSA"
  muestra e4-antes 60 60
  esperar_hasta "$t0" "$T_ANTES"
  log "E4: aplico netem en las 4 VM (200 ms ± 20 ms y 5 % de pérdida) durante $T_FALLA s"
  FALLA=netem
  ../chaos/e4_netem.sh aplicar
  tf=$(date +%s)
  sleep "$T_PAUSA"
  muestra e4-durante 150 90
  esperar_hasta "$tf" "$T_FALLA"
  log "E4: revierto netem"
  revertir
  if r=$(restos); then log "✓ sin netem en ninguna VM"; else log "✗ quedó netem:"; echo "$r"; fi
  esperar_completo "$(date +%s)"
  sleep "$T_DESPUES"
  verificar
  analizar e4 "$RES/e4_sonda_s3_$HORA.csv" "$RES/e4_sonda_meta_$HORA.csv"
  log "✓ E4 terminado"
}

e3() {
  local t0 tf
  T_ANTES=${T_ANTES:-30} T_FALLA=${T_FALLA:-60} T_DESPUES=${T_DESPUES:-30}
  empezar "$RES/e3_eventos.csv"
  t0=$(date +%s)
  sonda etcd e3-vm1 "$RES/e3_etcd_vm1_$HORA.csv" --nodos "${IPS[0]}:2379"
  sonda etcd e3-vm3 "$RES/e3_etcd_vm3_$HORA.csv" --nodos "${IPS[2]}:2379"
  sonda s3 e3-vm1 "$RES/e3_s3_vm1_$HORA.csv" --nodos "http://${IPS[0]}:9000"
  sonda s3 e3-vm3 "$RES/e3_s3_vm3_$HORA.csv" --nodos "http://${IPS[2]}:9000"
  esperar_hasta "$t0" "$T_ANTES"
  log "E3: aíslo vm3 de vm1, vm2 y vm4 durante $T_FALLA s (el anfitrión sigue llegando a todas)"
  FALLA=particion
  ../chaos/e3_particion.sh aislar vm3
  tf=$(date +%s)
  esperar_hasta "$tf" "$T_FALLA"
  log "E3: reunifico"
  revertir
  if r=$(restos); then log "✓ sin reglas de E3 en ninguna VM"; else log "✗ quedaron reglas:"; echo "$r"; fi
  esperar_completo "$(date +%s)"
  sleep "$T_DESPUES"
  parar_sondas
  log "consistencia final: ¿todos los nodos ven las escrituras confirmadas?"
  python -u probe.py etcd --comprobar "$RES/e3_etcd_vm1_$HORA.csv" "$RES/e3_etcd_vm3_$HORA.csv"
  python -u probe.py s3 --comprobar "$RES/e3_s3_vm1_$HORA.csv" "$RES/e3_s3_vm3_$HORA.csv"
  verificar
  analizar e3-etcd "$RES/e3_etcd_vm1_$HORA.csv" "$RES/e3_etcd_vm3_$HORA.csv"
  analizar e3-s3 "$RES/e3_s3_vm1_$HORA.csv" "$RES/e3_s3_vm3_$HORA.csv"
  log "✓ E3 terminado"
}

apagar() {  # apagar <vm>: E1, como un corte de luz
  APAGADAS+=("$1")
  FALLA=vm
  ../chaos/e1_caida_nodo.sh apagar "$1"
}

e1_uno() {
  local t0 tf
  T_ANTES=${T_ANTES:-60} T_FALLA=${T_FALLA:-150} T_DESPUES=${T_DESPUES:-30}
  empezar "$RES/e1_eventos.csv"
  t0=$(date +%s)
  sonda s3 e1-uno "$RES/e1_uno_sonda_s3_$HORA.csv"
  sonda meta e1-uno "$RES/e1_uno_sonda_meta_$HORA.csv"
  sleep "$T_PAUSA"
  muestra e1-antes 60 60
  esperar_hasta "$t0" "$T_ANTES"
  log "E1: apago vm4 de golpe (virsh destroy) durante $T_FALLA s"
  apagar vm4
  tf=$(date +%s)
  sleep "$T_PAUSA"
  muestra e1-uno 90 60
  log "lectura de las 1.000 actas con vm4 apagada (máx. 90 s)"
  timeout --foreground 90 python -u verify.py 2>&1 | tail -n 6
  esperar_hasta "$tf" "$T_FALLA"
  log "E1: prendo vm4"
  revertir
  esperar_completo "$(date +%s)"
  sleep "$T_DESPUES"
  verificar
  analizar e1-uno "$RES/e1_uno_sonda_s3_$HORA.csv" "$RES/e1_uno_sonda_meta_$HORA.csv"
  log "✓ E1 con un nodo terminado"
}

e1_dos() {
  local t0 tf
  T_ANTES=${T_ANTES:-60} T_FALLA=${T_FALLA:-120} T_DESPUES=${T_DESPUES:-30}
  empezar "$RES/e1_eventos.csv"
  t0=$(date +%s)
  sonda s3 e1-dos "$RES/e1_dos_sonda_s3_$HORA.csv"
  sonda meta e1-dos "$RES/e1_dos_sonda_meta_$HORA.csv"
  esperar_hasta "$t0" "$T_ANTES"
  log "E1: apago vm4 de golpe"
  apagar vm4
  sleep "$T_PAUSA"
  log "E1: apago vm3 de golpe: quedan 2 de 4 discos de MinIO y 2 de 3 miembros de etcd, durante $T_FALLA s"
  apagar vm3
  tf=$(date +%s)
  sleep "$T_PAUSA"
  log "lectura de las 1.000 actas con vm3 y vm4 apagadas (máx. 90 s): se espera que funcione"
  timeout --foreground 90 python -u verify.py 2>&1 | tail -n 6
  log "escritura con 2 de 4 discos: se espera que falle"
  muestra e1-dos 30 30
  esperar_hasta "$tf" "$T_FALLA"
  log "E1: prendo vm3 y, 20 s después, vm4"
  ../chaos/e1_caida_nodo.sh encender vm3
  APAGADAS=(vm4)
  sleep "$T_PAUSA"
  revertir
  esperar_completo "$(date +%s)"
  sleep "$T_DESPUES"
  verificar
  analizar e1-dos "$RES/e1_dos_sonda_s3_$HORA.csv" "$RES/e1_dos_sonda_meta_$HORA.csv"
  log "✓ E1 con dos nodos terminado"
}

case "$exp" in
  estado)
    if controles; then log "✓ estado estable"; else log "✗ hay algo fuera del estado estable"; fi
    "${SSH[@]}" vm1 "etcdctl --endpoints=$ETCD endpoint status -w table" 2>&1
    kubectl -n minio get pods -o custom-columns=POD:.metadata.name,FASE:.status.phase,NODO:.spec.nodeName 2>&1 ;;
  e4) e4 ;;
  e3) e3 ;;
  e1-uno) e1_uno ;;
  e1-dos) e1_dos ;;
esac
