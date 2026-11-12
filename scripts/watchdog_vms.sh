#!/usr/bin/env bash
# Agrega el watchdog virtual (i6300esb, acción reset) a las VM ya creadas y las reinicia de a una,
# con apagado ordenado, esperando que el clúster vuelva a estar completo antes de pasar a la siguiente.
# Si la VM después se congela, QEMU la reinicia sola. Origen: docs/postmortems/2026-11-12-vm3.md.
#
# Antes: ansible-playbook site.yml --tags watchdog (deja systemd listo para atender el watchdog).
# Uso, desde scripts/ en el anfitrión:   ./watchdog_vms.sh            (vm4, vm3, vm2 y vm1, en ese orden)
#                                         ./watchdog_vms.sh vm2        (sólo esa VM)
# vm1 va al final: es el servidor de k3s y suele ser el líder de etcd.
# Se detiene sin forzar nada si algún paso no se cumple a tiempo.
set -euo pipefail

SSH_CONFIG=${SSH_CONFIG:-../ansible/ssh_config}
SSH=(ssh -F "$SSH_CONFIG" -o ConnectTimeout=5 -o LogLevel=ERROR)
VIRSH=(virsh -c qemu:///system)
ETCD=192.168.56.11:2379,192.168.56.12:2379,192.168.56.13:2379
VMS=("$@"); [ ${#VMS[@]} -gt 0 ] || VMS=(vm4 vm3 vm2 vm1)

XML=$(mktemp)
trap 'rm -f "$XML"' EXIT
echo "<watchdog model='i6300esb' action='reset'/>" > "$XML"

# esperar <qué> <segundos> <comando...>: repite el comando cada 5 s hasta que salga bien
esperar() {
  local que=$1 max=$2; shift 2
  local t=0
  until "$@" >/dev/null 2>&1; do
    if [ "$t" -ge "$max" ]; then
      echo "  ✗ $que: no pasó en $max s. Me detengo acá, sin forzar nada." >&2
      exit 1
    fi
    sleep 5; t=$((t + 5))
  done
  echo "  ✓ $que (${t} s)"
}

# Clúster completo: 3 miembros de etcd sanos, 4 nodos Ready y 4 pods de MinIO listos
completo() {
  [ "$("${SSH[@]}" vm1 "etcdctl --endpoints=$ETCD endpoint health" 2>&1 | grep -c 'is healthy')" -eq 3 ] &&
  [ "$(kubectl get nodes --no-headers 2>/dev/null | awk '$2 == "Ready"' | wc -l)" -eq 4 ] &&
  [ "$(kubectl -n minio get pods --no-headers 2>/dev/null | awk '$2 == "1/1" && $3 == "Running"' | wc -l)" -eq 4 ]
}

apagada() { [ "$("${VIRSH[@]}" domstate "tif_$1")" = "shut off" ]; }
watchdog_activo() { "${SSH[@]}" "$1" "sudo journalctl -b -o cat --no-pager | grep -q 'Using hardware watchdog'"; }

echo "$(date +%H:%M:%S) Antes de empezar"
esperar "clúster completo" 60 completo

for vm in "${VMS[@]}"; do
  dom=tif_$vm
  echo "$(date +%H:%M:%S) $vm"
  if "${VIRSH[@]}" dumpxml --inactive "$dom" | grep -cE "<watchdog model=['\"]i6300esb" >/dev/null; then
    echo "  ✓ ya tenía el watchdog en su configuración"
  else
    "${VIRSH[@]}" attach-device "$dom" "$XML" --config >/dev/null
    echo "  ✓ watchdog agregado a la configuración (rige desde el próximo arranque)"
  fi
  "${VIRSH[@]}" shutdown "$dom" >/dev/null
  esperar "$vm apagada en orden" 120 apagada "$vm"
  "${VIRSH[@]}" start "$dom" >/dev/null
  esperar "$vm contesta por ssh" 180 "${SSH[@]}" "$vm" true
  esperar "watchdog activo en $vm" 90 watchdog_activo "$vm"
  "${SSH[@]}" "$vm" "sudo journalctl -b -o cat --no-pager | grep -m2 -E 'Using hardware watchdog|Watchdog running'" | sed 's/^/    /'
  esperar "clúster completo" 300 completo
done

echo "$(date +%H:%M:%S) Listo: ${VMS[*]} con watchdog, y el clúster completo."
