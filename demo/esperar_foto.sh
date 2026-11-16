#!/usr/bin/env bash
# Corre en la computadora desde la que se presenta (no en el anfitrión). Vigila una carpeta y, cuando
# aparece una foto nueva de WhatsApp («WhatsApp Image 2026-11-16 at 19.21.33.jpeg»), la copia como
# foto.jpg y la pasa al anfitrión, a /tmp/foto.jpg, lista para «demo/demo.sh subir /tmp/foto.jpg».
# Sigue vigilando: si llega otra foto, la reemplaza. Se corta con Ctrl+C.
#
# Uso:
#   demo/esperar_foto.sh <usuario@anfitrión> [carpeta]
#   demo/esperar_foto.sh tif@mi-servidor               # vigila ~/Descargas (o ~/Downloads)
#   demo/esperar_foto.sh tif@mi-servidor ~/Escritorio
#
# Solo toma las fotos que llegan después de arrancarlo. Necesita entrar al anfitrión por ssh sin
# contraseña (con la llave), como para el resto de la demo.
set -uo pipefail

destino=${1:?uso: esperar_foto.sh <usuario@anfitrión> [carpeta]}
carpeta=${2:-}
if [ -z "$carpeta" ]; then
  for c in "$HOME/Descargas" "$HOME/Downloads"; do [ -d "$c" ] && carpeta=$c && break; done
fi
[ -d "${carpeta:-}" ] || { echo "No existe la carpeta «${carpeta:-}»" >&2; exit 1; }
SCP=${DEMO_SCP:-scp}           # para probar sin anfitrión: DEMO_SCP=echo

marca=$(mktemp)                # solo cuentan los archivos que llegan (o se mueven ahí) después de este
trap 'rm -f "$marca"; echo; echo "Listo, dejé de vigilar."; exit 0' INT TERM

verde() { printf '\033[1;32m%s\033[0m\n' "$1"; }

echo "Vigilando $carpeta"
echo "Mandá la foto por WhatsApp y bajala ahí (en WhatsApp Web: Descargar). Ctrl+C para terminar."
echo

while true; do
  nueva=$(find "$carpeta" -maxdepth 1 -type f -iname 'WhatsApp Image*.jp*g' -cnewer "$marca" \
            -printf '%C@ %p\n' 2>/dev/null | sort -n | tail -n 1 | cut -d' ' -f2-)
  if [ -n "$nueva" ]; then
    # Esperar a que termine de bajar: tamaño mayor que cero, quieto un segundo y sin archivo .part al lado.
    t1=-1
    while :; do
      sleep 1
      t2=$(stat -c %s "$nueva" 2>/dev/null || echo 0)
      [ "$t2" -gt 0 ] && [ "$t2" = "$t1" ] && [ ! -e "$nueva.part" ] && [ ! -e "$nueva.crdownload" ] && break
      t1=$t2
    done
    touch "$marca"
    echo "Llegó: $(basename "$nueva") ($((t2 / 1024)) KB)"
    cp -f "$nueva" "$carpeta/foto.jpg"
    echo "   copiada como $carpeta/foto.jpg"
    if "$SCP" -q -o BatchMode=yes -o ConnectTimeout=10 "$carpeta/foto.jpg" "$destino:/tmp/foto.jpg"; then
      echo
      verde "✅ La foto ya está en el anfitrión. En la Terminal 1:"
      verde "      demo/demo.sh subir /tmp/foto.jpg"
      echo
    else
      echo "   ✗ No pude pasarla a $destino. A mano:  scp \"$carpeta/foto.jpg\" $destino:/tmp/foto.jpg"
    fi
    echo "Sigo vigilando por si llega otra (Ctrl+C para terminar)."
    echo
  fi
  sleep 1
done
