#!/usr/bin/env bash
# E1: caída de un nodo. Apaga la VM de golpe, como un corte de luz.
# (vagrant halt apaga de forma ordenada y no simula una caída.)
#
#   ./e1_caida_nodo.sh apagar vm4             # anota la hora exacta en results/e1_eventos.csv
#   ./e1_caida_nodo.sh encender vm4
#   ./e1_caida_nodo.sh apagar-ordenado vm4    # variante: apagado ordenado (como apretar el botón de
#                                             # encendido): los servicios se cierran y avisan a los demás
#
# Por defecto usa libvirt (la EXO). Con VirtualBox:  PROVEEDOR=virtualbox ./e1_caida_nodo.sh apagar vm4
set -euo pipefail
accion=${1:?uso: $0 apagar|encender <vm>}
vm=${2:?falta la VM, por ejemplo vm4}
proveedor=${PROVEEDOR:-libvirt}
eventos=${EVENTOS:-../results/e1_eventos.csv}

registrar() { printf '%s,%s,%s\n' "$(date +%s.%N)" "$accion" "$vm" >> "$eventos"; }

case "$proveedor:$accion" in
  virtualbox:apagar)   registrar; VBoxManage controlvm "$vm" poweroff ;;
  virtualbox:encender) registrar; VBoxManage startvm "$vm" --type headless ;;
  libvirt:apagar)      registrar; virsh -c qemu:///system destroy "tif_$vm" ;;
  libvirt:encender)    registrar; virsh -c qemu:///system start "tif_$vm" ;;
  virtualbox:apagar-ordenado) registrar; VBoxManage controlvm "$vm" acpipowerbutton ;;
  libvirt:apagar-ordenado)
    registrar; virsh -c qemu:///system shutdown "tif_$vm"
    for _ in $(seq 1 90); do      # hasta 90 s; si no se apaga, se corta de golpe y se avisa
      virsh -c qemu:///system domstate "tif_$vm" | grep -q 'shut off' && exit 0
      sleep 1
    done
    echo "tif_$vm no se apagó en 90 s: la apago de golpe" >&2
    virsh -c qemu:///system destroy "tif_$vm" ;;
  *) echo "acción o proveedor desconocido: $proveedor $accion" >&2; exit 1 ;;
esac
