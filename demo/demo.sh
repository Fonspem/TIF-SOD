#!/usr/bin/env bash
# Demo en vivo: cada paso es un comando corto, dice antes qué tiene que verse y deja todo como estaba.
# Los pasos que rompen algo (líder, nodo, partición) lo revierten solos, también con Ctrl+C.
# No escribe en results/ (salvo «estado», que guarda su salida como siempre): los eventos y las salidas
# van a /tmp/demo-tif/.
#
# Uso, en el anfitrión, con el entorno del TIF (venv activado, MINIO_USER, MINIO_PASS y KUBECONFIG):
#   demo/demo.sh estado               ¿está todo bien? (VM, nodos, etcd, MinIO, API)
#   demo/demo.sh subir <archivo>      sube un archivo real y registra su SHA-256 en etcd
#   demo/demo.sh ver <nombre>         muestra lo que etcd guarda de ese archivo
#   demo/demo.sh bajar <nombre>       lo baja y compara el hash (queda en /tmp/demo-tif/)
#   demo/demo.sh bloqueo              exclusión mutua: dos clientes a la vez y el fencing token
#   demo/demo.sh lider                mata al líder de etcd y mide cuánto tarda en haber otro
#   demo/demo.sh nodo [nombre]        apaga vm4 de golpe; al minuto baja el archivo (si se pasa el nombre);
#                                     con Enter la vuelve a prender
#   demo/demo.sh particion            aísla vm3 de las otras tres VM y prueba cada lado; Enter para reunificar
#   demo/demo.sh actas                verifica las 1.000 actas con su SHA-256
#   demo/demo.sh deshacer             por las dudas: reunifica vm3, prende vm4 y controla que no quede nada
#
# La guía con el orden, los tiempos y qué decir en cada paso está en demo/README.md.
set -uo pipefail

YO=$(readlink -f "$0")
RAIZ=$(cd "$(dirname "$YO")/.." && pwd)
cd "$RAIZ/scripts" || exit 1
TMP=/tmp/demo-tif
mkdir -p "$TMP"
export EVENTOS=$TMP/eventos.csv          # los scripts de chaos/ anotan acá en vez de en results/
SSH=(ssh -F "${SSH_CONFIG:-../ansible/ssh_config}" -o ConnectTimeout=5 -o LogLevel=ERROR)
ARCHIVO=(python -u ../demo/subir_y_verificar_archivo.py)

titulo() { printf '\n\033[1m== %s\033[0m\n' "$1"; }
esperas() { printf '   \033[2mTiene que verse: %s\033[0m\n\n' "$1"; }
esperar_enter() { printf '\n\033[1m%s\033[0m ' "$1"; read -r _; }
cuenta_atras() {  # cuenta_atras <segundos> <texto>
  local s
  for ((s = $1; s > 0; s--)); do printf '\r   %s: %3d s ' "$2" "$s"; sleep 1; done
  printf '\r%*s\r' 60 ''
}

etcd_put() {  # etcd_put <vm>: escribe una clave usando solo el etcd de esa VM
  "${SSH[@]}" "$1" "timeout 8 etcdctl --endpoints=127.0.0.1:2379 --command-timeout=5s put /demo/particion desde-$1" 2>&1 | tail -n 1
}

minio_quorum() {  # minio_quorum <ip>: 200 si ese nodo ve quórum de escritura; 503 si no
  curl -s -m 8 -o /dev/null -w '%{http_code}\n' "http://$1:9000/minio/health/cluster" || echo "sin respuesta en 8 s"
}

paso=${1:-}
case "$paso" in
  estado)
    titulo "Estado estable"
    esperas "todas las líneas con ✓"
    ../chaos/jornada.sh estado ;;

  subir)
    archivo=${2:?uso: demo/demo.sh subir <archivo>}
    titulo "Subir un archivo real: $(basename "$archivo")"
    esperas "el SHA-256 del archivo y «Registrado en etcd»"
    "${ARCHIVO[@]}" subir "$archivo" ;;

  ver)
    titulo "Qué guarda etcd del archivo"
    esperas "el mismo SHA-256, el tamaño y el estado «borrador»"
    "${ARCHIVO[@]}" ver "${2:?uso: demo/demo.sh ver <nombre>}" ;;

  bajar)
    titulo "Bajar el archivo y comprobar que está intacto"
    esperas "los dos hashes iguales y «OK: el archivo está intacto»"
    "${ARCHIVO[@]}" bajar "${2:?uso: demo/demo.sh bajar <nombre>}" --salida "$TMP/" ;;

  bloqueo)
    titulo "Exclusión mutua: dos clientes piden el bloqueo de la misma acta a la vez"
    esperas "uno recibe 200 y el otro 409"
    python -u lock_clients.py concurrencia --clientes 2
    titulo "Fencing token: el dueño viejo intenta firmar después de perder el bloqueo"
    esperas "el token viejo recibe 409 y el nuevo firma (tarda unos 20 s: espera a que venza el lease)"
    python -u lock_clients.py fencing ;;

  lider)
    titulo "Caída del líder de etcd (kill -9)"
    esperas "un líder nuevo en 1 o 2 s; en Grafana cambia «Líder actual de etcd»"
    python -u leader_election.py --modo kill --repeticiones 1 --eventos "$TMP/e2.csv" --salida "$TMP/e2-resultado.csv" ;;

  nodo)
    nombre=${2:-}
    titulo "Caída de un nodo: vm4 se apaga de golpe, como un corte de luz"
    esperas "en Grafana, vm4 en rojo y MinIO con 3 de 4 discos; etcd no cambia (vm4 no tiene miembro)"
    trap '../chaos/e1_caida_nodo.sh encender vm4; exit 130' INT
    ../chaos/e1_caida_nodo.sh apagar vm4
    cuenta_atras 60 "MinIO deja de esperar a vm4 (en la jornada tardó 58 s)"
    if [ -n "$nombre" ]; then
      titulo "Con vm4 apagada: bajar el archivo"
      esperas "«OK: el archivo está intacto»"
      "${ARCHIVO[@]}" bajar "$nombre" --salida "$TMP/"
    fi
    esperar_enter "Enter para volver a prender vm4…"
    trap - INT
    ../chaos/e1_caida_nodo.sh encender vm4
    echo "   vm4 arrancando: en la jornada, el clúster estuvo completo 17 s después." ;;

  particion)
    titulo "Partición de red: vm3 queda aislada de vm1, vm2 y vm4"
    esperas "del lado de vm3 (minoría) etcd no escribe y MinIO no tiene quórum; del lado de vm1 (mayoría), sí"
    trap '../chaos/e3_particion.sh revertir vm3 >/dev/null; echo; echo "   reunificado"; exit 130' INT
    ../chaos/e3_particion.sh aislar vm3
    cuenta_atras 10 "dejo que etcd note la partición"
    printf '   etcd desde vm3 (minoría): '; etcd_put vm3
    printf '   etcd desde vm1 (mayoría): '; etcd_put vm1
    printf '   MinIO según vm3 (quórum de escritura): '; minio_quorum 192.168.56.13
    printf '   MinIO según vm1 (quórum de escritura): '; minio_quorum 192.168.56.11
    printf '   servicio de metadatos (usa la mayoría): '
    curl -s -m 5 -o /dev/null -w '%{http_code}\n' localhost:8000/health
    esperar_enter "Enter para reunificar…"
    trap - INT
    ../chaos/e3_particion.sh revertir vm3
    cuenta_atras 15 "vm3 se pone al día"
    printf '   etcd desde vm3 otra vez: '; etcd_put vm3 ;;

  actas)
    titulo "Verificación de las 1.000 actas"
    esperas "OK: 1000 / 1000 (unos 5 s con el clúster completo; con un nodo caído, unos 40 s)"
    python -u verify.py --salida "$TMP/verificacion.csv" ;;

  deshacer)
    titulo "Dejar todo como estaba"
    ../chaos/e3_particion.sh revertir vm3 2>/dev/null || true     # si no estaba aislada, no hay reglas que borrar
    virsh -c qemu:///system domstate tif_vm4 | grep -q running || ../chaos/e1_caida_nodo.sh encender vm4
    echo "   Esperá un minuto y corré: demo/demo.sh estado" ;;

  *)
    sed -n '2,20p' "$YO" | cut -c3-
    exit 2 ;;
esac
