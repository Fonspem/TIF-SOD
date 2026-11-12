#!/usr/bin/env bash
# Prueba del watchdog: cuelga a propósito el núcleo de una VM (un kernel panic, como en el incidente
# de vm3) y mide cuánto tarda en volver sola, sin que nadie la reinicie.
# Origen: docs/postmortems/2026-11-12-vm3.md.
#
# Uso, desde scripts/ en el anfitrión:  ./probar_watchdog.sh vm4
# Conviene vm4: no tiene etcd, sólo MinIO, que sigue sirviendo con 3 de 4 discos.
# Anota la hora de cada evento en results/watchdog_eventos.csv.
set -euo pipefail

vm=${1:?Uso: ./probar_watchdog.sh vmN}
SSH_CONFIG=${SSH_CONFIG:-../ansible/ssh_config}
SSH=(ssh -F "$SSH_CONFIG" -o ConnectTimeout=5 -o LogLevel=ERROR)
VIRSH=(virsh -c qemu:///system)
ETCD=192.168.56.11:2379,192.168.56.12:2379,192.168.56.13:2379
EVENTOS=../results/watchdog_eventos.csv
[ -f "$EVENTOS" ] || echo "epoch,evento,vm" > "$EVENTOS"

registrar() { printf '%s,%s,%s\n' "$(date +%s.%N)" "$1" "$vm" >> "$EVENTOS"; }
arranque() { "${SSH[@]}" "$vm" cat /proc/sys/kernel/random/boot_id 2>/dev/null; }

# Clúster completo: 3 miembros de etcd sanos, 4 nodos Ready y MinIO listo en las 4 VM.
# etcd y MinIO se consultan directo (MinIO publica el 9000 en cada VM): el estado de los pods en
# Kubernetes tarda en actualizarse y, justo después de un reinicio rápido, todavía dice Running.
completo() {
  local ip
  [ "$("${SSH[@]}" vm1 "etcdctl --endpoints=$ETCD endpoint health" 2>&1 | grep -c 'is healthy')" -eq 3 ] &&
  [ "$(kubectl get nodes --no-headers 2>/dev/null | awk '$2 == "Ready"' | wc -l)" -eq 4 ] || return 1
  for ip in 192.168.56.11 192.168.56.12 192.168.56.13 192.168.56.14; do
    curl -sf -m 3 -o /dev/null "http://$ip:9000/minio/health/ready" || return 1
  done
}

# Controles antes de colgarla: si alguno falla, no se toca nada
completo || { echo "El clúster no está completo: no sigo." >&2; exit 1; }
"${SSH[@]}" "$vm" "sudo journalctl -b -o cat --no-pager | grep -q 'Using hardware watchdog'" ||
  { echo "El watchdog no está activo en $vm: no sigo." >&2; exit 1; }
antes=$(arranque)
echo "$(date +%H:%M:%S) Controles bien: clúster completo y watchdog activo en $vm"

# libvirt avisa cuando el watchdog dispara: se escucha ese evento desde antes de colgarla
evento=$(mktemp)
trap 'rm -f "$evento"' EXIT
"${VIRSH[@]}" event --domain "tif_$vm" --event watchdog --timeout 300 --timestamp > "$evento" 2>&1 &
escucha=$!
sleep 1

echo "$(date +%H:%M:%S) Cuelgo el núcleo de $vm"
t0=$(date +%s)
registrar colgar
timeout 10 "${SSH[@]}" "$vm" "sudo sh -c 'echo c > /proc/sysrq-trigger'" >/dev/null 2>&1 || true

echo "  esperando a que vuelva sola (sin virsh ni nada)…"
until ahora=$(arranque) && [ -n "$ahora" ] && [ "$ahora" != "$antes" ]; do
  if [ $(( $(date +%s) - t0 )) -ge 300 ]; then
    echo "  ✗ $vm no volvió en 5 minutos. No toques nada y revisá la consola de la VM." >&2
    exit 1
  fi
  sleep 2
done
registrar volvio
echo "$(date +%H:%M:%S) ✓ $vm volvió sola en $(( $(date +%s) - t0 )) s, con un arranque nuevo"
kill "$escucha" 2>/dev/null || true
wait "$escucha" 2>/dev/null || true
if grep -q "event 'watchdog'" "$evento"; then
  echo "  ✓ libvirt registró el disparo del watchdog (hora UTC): $(grep -m1 "event 'watchdog'" "$evento")"
else
  echo "  ⚠️ libvirt no registró el disparo del watchdog: la VM volvió por otro motivo. Revisá el registro de libvirt."
fi

until completo; do
  if [ $(( $(date +%s) - t0 )) -ge 600 ]; then
    echo "  ✗ el clúster no se completó en 10 minutos. Revisá chaos/jornada.sh estado." >&2
    exit 1
  fi
  sleep 5
done
registrar completo
echo "$(date +%H:%M:%S) ✓ clúster completo otra vez, $(( $(date +%s) - t0 )) s después de colgarla"
"${SSH[@]}" "$vm" "sudo journalctl -b -o cat --no-pager | grep -m1 'Using hardware watchdog'" | sed 's/^/    /'
