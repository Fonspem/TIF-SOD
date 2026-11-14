# demo/: la demostración en vivo

Todo lo que hace falta para mostrar el sistema funcionando y fallando delante de alguien. Cada paso es un comando corto que primero dice qué tiene que verse y, si rompe algo, lo arregla solo al terminar (también con Ctrl+C).

| Archivo | Qué hace |
|---|---|
| `demo.sh` | Corre cada paso de la demo: `demo/demo.sh <paso>`. Sin argumentos, lista los pasos |
| `subir_y_verificar_archivo.py` | Sube un archivo cualquiera (una foto, un PDF), registra su SHA-256 en etcd y lo vuelve a bajar comprobando que llegó intacto. Lo usa `demo.sh`, pero se puede correr solo |

## Antes de empezar

En el anfitrión, con el clúster prendido (`scripts/tif prender` o los pasos del [README](../README.md#cómo-levantarlo)):

```bash
cd TIF-SOD && . .venv/bin/activate
export MINIO_USER=admin MINIO_PASS='<contraseña>' KUBECONFIG=$PWD/kubeconfig
demo/demo.sh estado            # todo con ✓
```

Grafana abierto en `http://<anfitrión>:3000/d/tif-estado`, con los últimos 15 minutos.

## Los pasos

| Paso | Qué muestra | Qué tiene que verse | Tarda |
|---|---|---|---|
| `estado` | Que todo está bien antes de empezar | Todas las líneas con ✓ | 20 s |
| `subir <archivo>` | Carga de un documento: va a MinIO y su huella (SHA-256) a etcd | El hash y «Registrado en etcd» | 15 s |
| `ver <nombre>` | Lo que etcd guarda del documento | Hash, tamaño y estado «borrador» | 5 s |
| `bajar <nombre>` | Integridad: lo baja y recalcula el hash | Los dos hashes iguales y «OK: el archivo está intacto» | 10 s |
| `bloqueo` | Exclusión mutua: dos clientes a la vez y el fencing token | Un 200 y un 409; el token viejo rechazado con 409 | 40 s |
| `lider` | Caída del líder de etcd (`kill -9`) | Un líder nuevo en 1 o 2 s; en Grafana cambia «Líder actual de etcd» | 40 s |
| `nodo [nombre]` | Caída de un nodo: vm4 apagada de golpe. Al minuto baja el archivo; con Enter, la prende | vm4 en rojo, MinIO con 3 de 4 discos y el archivo intacto | 1,5 a 2 min |
| `particion` | Partición de red: vm3 aislada de las otras tres. Prueba cada lado; con Enter, reunifica | En vm3 (minoría), etcd no escribe y MinIO no tiene quórum; en vm1 (mayoría), sí; la API sigue respondiendo | 1 a 1,5 min |
| `actas` | Las 1.000 actas, una por una, con su SHA-256 | `OK: 1000 / 1000` | 5 s (40 s con un nodo caído) |
| `deshacer` | Por las dudas: reunifica vm3 y prende vm4 | — | 5 s |

El nombre de un archivo subido es su nombre sin la extensión: `subir /tmp/foto.jpg` → `ver foto`, `bajar foto`, `nodo foto`.

## Dos recorridos armados

**Completo: lo que pide el enunciado** (carga de documentos, caída de un nodo y del líder de etcd, partición de red y verificación de integridad), unos 8 minutos de comandos, más lo que se hable:

```bash
demo/demo.sh estado
demo/demo.sh subir /tmp/foto.jpg && demo/demo.sh ver foto
demo/demo.sh bloqueo
demo/demo.sh lider
demo/demo.sh nodo foto          # al minuto baja la foto con vm4 apagada; Enter para prenderla
demo/demo.sh particion          # Enter para reunificar
demo/demo.sh actas
demo/demo.sh estado
```

**Corto: unos 5 minutos**, para cuando el tiempo aprieta (la partición se cuenta con la diapositiva de E3):

```bash
demo/demo.sh estado
demo/demo.sh subir /tmp/foto.jpg && demo/demo.sh ver foto
demo/demo.sh lider
demo/demo.sh nodo foto
demo/demo.sh estado
```

## Si algo sale mal

- **Se cortó un paso a la mitad** (se cerró la terminal, se colgó): `demo/demo.sh deshacer` y, al minuto, `demo/demo.sh estado`.
- **`bajar` falla o tarda con vm4 recién apagada:** es lo que pasó en E1, MinIO tarda cerca de un minuto en dejar de esperar a un nodo que muere sin avisar. Por eso `nodo` espera 60 s antes de bajar. Si igual falla, repetir `demo/demo.sh bajar foto`.
- **En la partición, etcd escribe desde vm3:** las reglas no llegaron a aplicarse. Ver `chaos/e3_particion.sh` y repetir.
- Los resultados de la demo quedan en `/tmp/demo-tif/` y no se mezclan con los de la jornada de caos en `results/`.

## Por qué cada paso funciona así

- **`nodo` espera un minuto antes de bajar:** en E1, con un nodo apagado de golpe, MinIO pasó 58 s sin completar una lectura. Después siguió con 3 de 4 discos (detalle en `docs/postmortems/2026-11-13-e1.md`).
- **`particion` prueba etcd desde cada VM** (`etcdctl` contra el etcd local de vm3 y de vm1), porque desde el anfitrión se llega a las dos y no se vería la diferencia. El servicio de metadatos sigue respondiendo porque habla con todos los miembros y encuentra la mayoría.
- **`lider` usa `kill -9`:** es la caída sin aviso. Con `systemctl stop`, el líder transfiere el liderazgo antes de irse y el cambio tarda unos 60 ms (E2).
