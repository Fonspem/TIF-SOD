#!/usr/bin/env bash
# E4, la variante que usa el TIF: 200 ms de latencia y 5 % de pérdida con tc netem
# en la interfaz privada de cada VM (la que tiene la IP 192.168.56.x). Afecta a todo
# el tráfico entre nodos: MinIO, etcd y k3s.
#
#   ./e4_netem.sh aplicar     # en las 4 VM
#   ./e4_netem.sh revertir
set -euo pipefail
accion=${1:?uso: $0 aplicar|revertir}
SSH_CONFIG=${SSH_CONFIG:-../ansible/ssh_config}
iface='$(ip -o -4 addr show | awk "/192\.168\.56\./ {print \$2}")'

case "$accion" in
  aplicar)  remoto="sudo tc qdisc replace dev $iface root netem delay 200ms 20ms loss 5% 25%" ;;
  revertir) remoto="sudo tc qdisc del dev $iface root 2>/dev/null || true" ;;
  *) echo "acción desconocida: $accion" >&2; exit 1 ;;
esac

printf '%s,%s\n' "$(date +%s.%N)" "$accion" >> "${EVENTOS:-../results/e4_eventos.csv}"
for vm in vm1 vm2 vm3 vm4; do
  ssh -F "$SSH_CONFIG" "$vm" "$remoto" && echo "$accion en $vm"
done
