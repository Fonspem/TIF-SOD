#!/usr/bin/env bash
# E3: partición de red. Aísla una VM de las otras tres; el anfitrión sigue
# llegando a ambos lados, para que el cliente pueda medir qué responde cada uno.
#
#   ./e3_particion.sh aislar vm3
#   ./e3_particion.sh revertir vm3
#
# Se insertan y se borran sólo estas reglas: nunca "iptables -F", que también
# borraría las reglas de k3s y dejaría al clúster sin red.
set -euo pipefail
accion=${1:?uso: $0 aislar|revertir <vm>}
vm=${2:?falta la VM, por ejemplo vm3}
SSH_CONFIG=${SSH_CONFIG:-../ansible/ssh_config}
declare -A IP=([vm1]=192.168.56.11 [vm2]=192.168.56.12 [vm3]=192.168.56.13 [vm4]=192.168.56.14)

otras=""
for nombre in "${!IP[@]}"; do
  [[ $nombre == "$vm" ]] || otras+="${IP[$nombre]} "
done

case "$accion" in
  aislar)   op="-I" ;;
  revertir) op="-D" ;;
  *) echo "acción desconocida: $accion" >&2; exit 1 ;;
esac

remoto="for ip in $otras; do sudo iptables $op INPUT -s \$ip -j DROP; sudo iptables $op OUTPUT -d \$ip -j DROP; done"
printf '%s,%s,%s\n' "$(date +%s.%N)" "$accion" "$vm" >> "${EVENTOS:-../results/e3_eventos.csv}"
ssh -F "$SSH_CONFIG" "$vm" "$remoto"
echo "$accion $vm (otras VM: $otras)"
