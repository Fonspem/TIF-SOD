#!/usr/bin/env bash
# Respaldo de los metadatos (etcd). Sección 6.4 del informe y docs/runbook.md.
#
#   ./respaldo.sh etcd
#       toma una instantánea de etcd en vm1 y la copia a ../respaldo/etcd-AAAAMMDD-HHMM.db
#   ./respaldo.sh probar-etcd ../respaldo/etcd-AAAAMMDD-HHMM.db
#       la restaura en un etcd temporal de vm1 (puertos 32379 y 32380), que no toca
#       al clúster, y cuenta las actas registradas en ella
#
# La copia de las actas la hace verify.py --copia ../respaldo/actas.
set -euo pipefail
SSH_CONFIG=${SSH_CONFIG:-../ansible/ssh_config}
DESTINO=${DESTINO:-../respaldo}
accion=${1:?uso: $0 etcd | probar-etcd <instantánea>}

case "$accion" in
  etcd)
    mkdir -p "$DESTINO"
    archivo="$DESTINO/etcd-$(date +%Y%m%d-%H%M).db"
    # Sin el timeout, etcdctl espera para siempre si el miembro de vm1 no responde
    ssh -F "$SSH_CONFIG" vm1 'timeout 60 etcdctl --endpoints=127.0.0.1:2379 snapshot save /tmp/etcd-respaldo.db \
      >/tmp/etcd-respaldo.log 2>&1 || { tail -3 /tmp/etcd-respaldo.log >&2; echo "etcd de vm1 no entregó la instantánea" >&2; exit 1; }'
    scp -q -F "$SSH_CONFIG" vm1:/tmp/etcd-respaldo.db "$archivo"
    echo "Instantánea de etcd: $archivo ($(du -h "$archivo" | cut -f1))"
    ;;
  probar-etcd)
    archivo=${2:?falta la instantánea, por ejemplo ../respaldo/etcd-20261112-1030.db}
    scp -q -F "$SSH_CONFIG" "$archivo" vm1:/tmp/etcd-prueba.db
    ssh -F "$SSH_CONFIG" vm1 bash -s <<'FIN'
set -euo pipefail
# etcdutl queda en /usr/local/bin con el playbook actual; si no, se usa el del paquete descargado
ETCDUTL=$(command -v etcdutl || ls /opt/etcd-v*-linux-amd64/etcdutl 2>/dev/null | head -1 || true)
[ -n "$ETCDUTL" ] || { echo "falta etcdutl en vm1: volver a correr el playbook de Ansible" >&2; exit 1; }
D=$(mktemp -d)
# La restauración comprueba el hash de integridad que etcdctl snapshot save agregó a la instantánea
"$ETCDUTL" snapshot restore /tmp/etcd-prueba.db --name prueba --data-dir "$D/datos" \
  --initial-cluster prueba=http://127.0.0.1:32380 \
  --initial-advertise-peer-urls http://127.0.0.1:32380 >"$D/restaurar.log" 2>&1 \
  || { tail -5 "$D/restaurar.log" >&2; exit 1; }
etcd --name prueba --data-dir "$D/datos" --listen-client-urls http://127.0.0.1:32379 \
  --advertise-client-urls http://127.0.0.1:32379 --listen-peer-urls http://127.0.0.1:32380 \
  >"$D/etcd.log" 2>&1 &
P=$!
trap 'kill $P 2>/dev/null || true' EXIT
for _ in $(seq 20); do
  etcdctl --endpoints=127.0.0.1:32379 endpoint health >/dev/null 2>&1 && break
  sleep 0.5
done
# /docs/acta-NNNN son las actas; las sondas de los experimentos registran /docs/sonda-…
docs=$(etcdctl --endpoints=127.0.0.1:32379 get --prefix /docs/ --keys-only | grep -c . || true)
actas=$(etcdctl --endpoints=127.0.0.1:32379 get --prefix /docs/acta- --keys-only | grep -c . || true)
echo "Restauración correcta. Actas registradas en la instantánea: $actas (documentos en total, con los de las sondas: $docs)"
FIN
    ;;
  *) echo "acción desconocida: $accion" >&2; exit 1 ;;
esac
