"""Sonda de estado estable para los experimentos E1 a E4.

Hace lecturas y escrituras periódicas contra un objetivo y anota cada pedido en
un CSV: momento, nodo que respondió, operación, resultado, latencia y error.
Lecturas y escrituras corren en hilos separados, así una escritura trabada no
frena las lecturas. Con esos CSV, analyze.py calcula la disponibilidad, los
errores, la latencia p95 y los cortes de servicio alrededor de cada falla.

Objetivos:
  s3    MinIO. Lee siempre un objeto «ancla» escrito al empezar (con unidades
        caídas, eso obliga a reconstruirlo) y escribe un objeto nuevo de 4 KiB
        por ciclo, en el bucket «sonda».
  etcd  Lectura linealizable de una clave ancla y escritura de una clave nueva
        por ciclo, por la API HTTP de etcd.
  meta  Servicio de metadatos: GET /health como lectura y alta de un documento
        nuevo como escritura.

--nodos elige con qué nodos hablar. Con uno solo, la sonda mide ese nodo (en E3,
un lado y el otro de la partición). Con varios, se comporta como un cliente con
conmutación: usa el último que respondió y, si falla, prueba el siguiente.

Ejemplos (desde scripts/, con MINIO_USER y MINIO_PASS definidas):
  python probe.py s3 --etiqueta e1 --salida ../results/e1_sonda_s3.csv
  python probe.py meta --etiqueta e2 --intervalo 0.1 --salida ../results/e2_sonda_meta.csv
  python probe.py etcd --nodos 192.168.56.13:2379 --etiqueta e3-vm3 --salida ../results/e3_etcd_vm3.csv
  python probe.py etcd --nodos 192.168.56.11:2379 --etiqueta e3-vm1 --salida ../results/e3_etcd_vm1.csv

Después de revertir E3, la consistencia final (¿todos los nodos ven lo mismo?):
  python probe.py etcd --comprobar ../results/e3_etcd_vm1.csv ../results/e3_etcd_vm3.csv
  python probe.py s3 --comprobar ../results/e3_s3_vm1.csv ../results/e3_s3_vm3.csv

La sonda se detiene con Ctrl+C o al cumplirse --duracion.
"""
import argparse
import base64
import csv
import hashlib
import os
import signal
import sys
import threading
import time
from pathlib import Path

import requests

from medidas import cortes, percentil

RESULTADOS = Path(__file__).resolve().parent.parent / "results"
ETCD = os.environ.get("ETCD", "192.168.56.11:2379,192.168.56.12:2379,192.168.56.13:2379")
META_API = os.environ.get("META_API", "http://localhost:5000")
TIMEOUT = {"s3": 5.0, "etcd": 2.0, "meta": 8.0}  # el de meta cubre la conmutación interna del servicio
COLUMNAS = ["t", "objetivo", "etiqueta", "nodo", "op", "ok", "ms", "clave", "error"]
OPERACIONES = ("lectura", "escritura")


class Falla(Exception):
    def __init__(self, nodo, detalle):
        super().__init__(detalle)
        self.nodo, self.detalle = nodo, detalle


def describir(e):
    """Texto corto para la columna error."""
    if isinstance(e, Falla):
        return e.detalle
    respuesta = getattr(e, "response", None)
    if isinstance(respuesta, dict) and "Error" in respuesta:  # ClientError de botocore
        estado = respuesta.get("ResponseMetadata", {}).get("HTTPStatusCode", "")
        return f"HTTP {estado} {respuesta['Error'].get('Code', '')}".strip()
    texto = str(e).lower()
    for frase, corto in (("refused", "conexión rechazada"), ("no route", "sin ruta al host"),
                         ("unreachable", "red inalcanzable"), ("timed out", "tiempo agotado"),
                         ("timeout", "tiempo agotado")):
        if frase in texto:
            return f"{type(e).__name__} ({corto})"
    return type(e).__name__


class Conmutador:
    """Prueba los nodos en orden, empezando por el último que respondió."""

    def __init__(self, nodos):
        self.nodos, self.preferido = nodos, 0

    def __call__(self, operacion):
        errores = []
        for i in range(len(self.nodos)):
            idx = (self.preferido + i) % len(self.nodos)
            try:
                operacion(self.nodos[idx])
            except Exception as e:  # noqa: BLE001 (cualquier falla pasa al siguiente nodo)
                errores.append(describir(e))
                continue
            self.preferido = idx
            return self.nodos[idx]
        nodo = self.nodos[0] if len(self.nodos) == 1 else "ninguno"
        distintos = list(dict.fromkeys(errores))
        raise Falla(nodo, " | ".join(distintos)[:160])


def contenido(clave, tam):
    """Contenido determinístico de cada objeto: se puede recalcular para comprobarlo."""
    bloque = hashlib.sha256(clave.encode()).digest()
    return (bloque * (tam // len(bloque) + 1))[:tam]


def valor(clave):
    return hashlib.sha256(clave.encode()).hexdigest()


def b64(texto):
    return base64.b64encode(texto.encode()).decode()


class S3:
    def __init__(self, args):
        from botocore.config import Config

        import common
        cfg = Config(connect_timeout=args.timeout, read_timeout=args.timeout,
                     retries={"total_max_attempts": 1, "mode": "standard"})
        self.clientes = {n: common.s3(n, cfg) for n in args.nodos}
        self.bucket, self.tam = args.bucket, args.tam
        self.conmutar = Conmutador(args.nodos)

    def preparar(self, ancla):
        from botocore.exceptions import ClientError

        def op(nodo):
            c = self.clientes[nodo]
            try:
                c.head_bucket(Bucket=self.bucket)
            except ClientError as e:
                if e.response["Error"]["Code"] not in ("404", "NoSuchBucket"):
                    raise
                c.create_bucket(Bucket=self.bucket)
            c.put_object(Bucket=self.bucket, Key=ancla, Body=contenido(ancla, self.tam))
        return self.conmutar(op)

    def leer(self, clave):
        def op(nodo):
            datos = self.clientes[nodo].get_object(Bucket=self.bucket, Key=clave)["Body"].read()
            if datos != contenido(clave, self.tam):
                raise Falla(nodo, "contenido distinto")
        return self.conmutar(op)

    def escribir(self, clave):
        datos = contenido(clave, self.tam)
        return self.conmutar(lambda nodo: self.clientes[nodo].put_object(Bucket=self.bucket, Key=clave, Body=datos))

    def vista(self, nodo, prefijos):
        """Para --comprobar: {clave: (bytes, etag)} de lo que lista ese nodo."""
        vista = {}
        paginador = self.clientes[nodo].get_paginator("list_objects_v2")
        for prefijo in prefijos:
            for pagina in paginador.paginate(Bucket=self.bucket, Prefix=prefijo):
                for o in pagina.get("Contents", []):
                    vista[o["Key"]] = (o["Size"], o["ETag"].strip('"'))
        return vista

    def esperado(self, clave):
        # Para objetos subidos en una sola parte y sin cifrar, el ETag es el MD5 del contenido.
        return self.tam, hashlib.md5(contenido(clave, self.tam), usedforsecurity=False).hexdigest()


class Etcd:
    def __init__(self, args):
        self.sesion, self.timeout = requests.Session(), args.timeout
        self.conmutar = Conmutador(args.nodos)
        self.revision = {}

    def _pedido(self, nodo, ruta, cuerpo):
        r = self.sesion.post(f"http://{nodo}/v3/{ruta}", json=cuerpo, timeout=self.timeout)
        try:
            datos = r.json()
        except ValueError:
            datos = {}
        if r.status_code != 200 or "error" in datos or "code" in datos:
            raise Falla(nodo, f"HTTP {r.status_code} {datos.get('message') or datos.get('error') or ''}".strip())
        return datos

    def preparar(self, ancla):
        return self.escribir(ancla)

    def leer(self, clave):
        def op(nodo):
            kvs = self._pedido(nodo, "kv/range", {"key": b64(clave)}).get("kvs", [])
            if not kvs or base64.b64decode(kvs[0].get("value", "")).decode() != valor(clave):
                raise Falla(nodo, "valor distinto o ausente")
        return self.conmutar(op)

    def escribir(self, clave):
        return self.conmutar(lambda nodo: self._pedido(nodo, "kv/put", {"key": b64(clave), "value": b64(valor(clave))}))

    def vista(self, nodo, prefijos):
        """Para --comprobar: {clave: valor} según el estado local del miembro (lectura serializable)."""
        vista = {}
        for prefijo in prefijos:
            fin = prefijo[:-1] + chr(ord(prefijo[-1]) + 1)
            datos = self._pedido(nodo, "kv/range", {"key": b64(prefijo), "range_end": b64(fin), "serializable": True})
            for kv in datos.get("kvs", []):
                vista[base64.b64decode(kv["key"]).decode()] = base64.b64decode(kv.get("value", "")).decode()
            self.revision[nodo] = int(datos["header"]["revision"])
        return vista

    def esperado(self, clave):
        return valor(clave)


class Meta:
    def __init__(self, args):
        self.api, self.timeout = args.api.rstrip("/"), args.timeout
        self.sesion = requests.Session()

    def _pedido(self, metodo, ruta, esperado):
        try:
            r = self.sesion.request(metodo, self.api + ruta, json={} if metodo == "POST" else None,
                                    timeout=self.timeout)
        except requests.RequestException as e:
            raise Falla(self.api, describir(e)) from e
        if r.status_code != esperado:
            try:
                detalle = r.json().get("error", "")
            except ValueError:
                detalle = ""
            raise Falla(self.api, f"HTTP {r.status_code} {detalle}".strip())
        return self.api

    def preparar(self, ancla):
        return None

    def leer(self, clave):
        return self._pedido("GET", "/health", 200)

    def escribir(self, clave):
        return self._pedido("POST", f"/docs/{clave}", 201)


OBJETIVOS = {"s3": S3, "etcd": Etcd, "meta": Meta}


def prefijo_de_claves(objetivo, etiqueta, corrida):
    if objetivo == "meta":  # el nombre del documento va en la URL: sin barras
        return f"sonda-{etiqueta}-{corrida}-"
    return f"{'/' if objetivo == 'etcd' else ''}sonda/{etiqueta}/{corrida}/"


class Registro:
    """CSV compartido por los hilos, más lo necesario para el informe en vivo."""

    def __init__(self, ruta):
        nuevo = not os.path.exists(ruta) or os.path.getsize(ruta) == 0
        if not nuevo:
            print(f"Aviso: {ruta} ya existe; las filas nuevas se agregan al final.")
        self.archivo = open(ruta, "a", newline="")
        self.csv = csv.writer(self.archivo)
        if nuevo:
            self.csv.writerow(COLUMNAS)
        self.lock = threading.Lock()
        self.pedidos = {op: [] for op in OPERACIONES}   # (t, ok, ms) de toda la corrida
        self.parcial = {op: [] for op in OPERACIONES}   # desde el último informe
        self.ultimo_error = ""

    def anotar(self, fila):
        with self.lock:
            if self.archivo.closed:  # un pedido que terminó después de cerrar la sonda
                return
            self.csv.writerow([fila[c] for c in COLUMNAS])
            self.archivo.flush()
            dato = (fila["t"], fila["ok"], fila["ms"])
            self.pedidos[fila["op"]].append(dato)
            self.parcial[fila["op"]].append(dato)
            if not fila["ok"]:
                self.ultimo_error = f"{fila['error']} ({fila['nodo']})"

    def tomar_parcial(self):
        with self.lock:
            parcial, error = self.parcial, self.ultimo_error
            self.parcial, self.ultimo_error = {op: [] for op in OPERACIONES}, ""
        return parcial, error

    def cerrar(self):
        with self.lock:
            self.archivo.close()


def trabajador(op, objetivo, args, registro, detener, prefijo, ancla):
    proximo, n = time.monotonic(), 0
    while not detener.is_set():
        n += 1
        clave = f"{prefijo}{n:07d}" if op == "escritura" else ancla
        t, t0 = time.time(), time.perf_counter()
        try:
            nodo = objetivo.escribir(clave) if op == "escritura" else objetivo.leer(clave)
            ok, error = 1, ""
        except Exception as e:  # noqa: BLE001 (toda falla se anota y la sonda sigue)
            nodo, ok, error = getattr(e, "nodo", "?"), 0, describir(e)
        registro.anotar({"t": round(t, 3), "objetivo": args.objetivo, "etiqueta": args.etiqueta, "nodo": nodo,
                         "op": op, "ok": ok, "ms": round((time.perf_counter() - t0) * 1000, 1),
                         "clave": clave if op == "escritura" else "", "error": error})
        proximo += args.intervalo
        espera = proximo - time.monotonic()
        if espera > 0:
            detener.wait(espera)
        else:
            proximo = time.monotonic()  # venimos atrasados: no acumular una ráfaga de pedidos


def linea_de_estado(pedidos):
    if not pedidos:
        return "sin pedidos"
    ok = [ms for _, bien, ms in pedidos if bien]
    texto = f"{len(ok)}/{len(pedidos)} ok"
    return texto + (f", p95 {percentil(ok, 95):.0f} ms" if ok else "")


def resumen(registro, args, segundos):
    print(f"\nResumen ({args.objetivo}, {args.etiqueta}, {segundos:.0f} s):")
    for op in OPERACIONES:
        pedidos = sorted(registro.pedidos[op])
        if not pedidos:
            continue
        ok = [ms for _, bien, ms in pedidos if bien]
        mayor = max(((fin or pedidos[-1][0]) - inicio for inicio, fin, _ in cortes([(t, b) for t, b, _ in pedidos])),
                    default=0)
        texto = f"  {op:<10} {len(pedidos)} pedidos, {len(ok)} ok ({100 * len(ok) / len(pedidos):.1f} %)"
        if ok:
            texto += f", p50 {percentil(ok, 50):.0f} ms, p95 {percentil(ok, 95):.0f} ms"
        print(texto + f", corte más largo {mayor:.1f} s")


def sondear(args, clase):
    corrida = time.strftime("%Y%m%d-%H%M%S")
    prefijo = prefijo_de_claves(args.objetivo, args.etiqueta, corrida)
    ancla = prefijo + "ancla"
    salida = args.salida or str(RESULTADOS / f"sonda_{args.etiqueta}_{args.objetivo}_{corrida}.csv")
    operaciones = [args.solo] if args.solo else list(OPERACIONES)

    instancias = {op: clase(args) for op in operaciones}  # cada hilo con sus propios clientes
    try:
        instancias[operaciones[0]].preparar(ancla)
    except Exception as e:  # noqa: BLE001
        sys.exit(f"No se pudo preparar la sonda (bucket o clave ancla): {describir(e)}")

    registro = Registro(salida)
    detener = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: detener.set())
    signal.signal(signal.SIGTERM, lambda *_: detener.set())
    hilos = [threading.Thread(target=trabajador, daemon=True,
                              args=(op, instancias[op], args, registro, detener, prefijo, ancla))
             for op in operaciones]
    nodos = args.api if args.objetivo == "meta" else ", ".join(args.nodos)
    print(f"Sonda {args.objetivo} contra {nodos}: un pedido de cada tipo cada {args.intervalo} s. "
          f"Ctrl+C para terminar.\nCSV: {salida}")
    inicio = time.monotonic()
    for h in hilos:
        h.start()
    proximo_informe = inicio + args.informe
    while not detener.wait(0.2):
        ahora = time.monotonic()
        if args.duracion and ahora - inicio >= args.duracion:
            detener.set()
        elif args.informe and ahora >= proximo_informe:
            proximo_informe += args.informe
            parcial, error = registro.tomar_parcial()
            estado = " | ".join(f"{op}s {linea_de_estado(parcial[op])}" for op in operaciones)
            print(f"[+{ahora - inicio:5.0f} s] {estado}" + (f" | error: {error}" if error else ""), flush=True)
    for h in hilos:
        h.join(timeout=args.timeout + 1)
    registro.cerrar()
    resumen(registro, args, time.monotonic() - inicio)
    print(f"CSV: {salida}")
    return 0


def comprobar(args, clase):
    """Consistencia final: qué escrituras de los CSV ve cada nodo."""
    escrituras = {}  # clave -> confirmada al cliente
    for ruta in args.comprobar:
        with open(ruta, newline="") as f:
            for fila in csv.DictReader(f):
                if fila["op"] == "escritura" and fila["clave"]:
                    escrituras[fila["clave"]] = escrituras.get(fila["clave"], False) or fila["ok"] == "1"
    if not escrituras:
        sys.exit("Los CSV no tienen escrituras para comprobar.")
    prefijos = sorted({clave.rsplit("/", 1)[0] + "/" for clave in escrituras})
    confirmadas = {c for c, ok in escrituras.items() if ok}
    objetivo = clase(args)

    for intento in range(1, args.reintentos + 1):
        filas, conjuntos, problemas = [], {}, []
        for nodo in args.nodos:
            try:
                vista = objetivo.vista(nodo, prefijos)
            except Exception as e:  # noqa: BLE001
                filas.append(f"| {nodo} | no respondió: {describir(e)} | | | |")
                problemas.append(f"{nodo} no respondió")
                continue
            presentes = {c for c in escrituras if c in vista}
            faltan = confirmadas - presentes
            distintas = {c for c in presentes if vista[c] != objetivo.esperado(c)}
            conjuntos[nodo] = frozenset(presentes)
            filas.append(f"| {nodo} | {len(confirmadas & presentes)} | {len(faltan)} | "
                         f"{len(presentes - confirmadas)} | {len(distintas)} |")
            if faltan:
                problemas.append(f"a {nodo} le faltan {len(faltan)} escrituras confirmadas")
            if distintas:
                problemas.append(f"{nodo} tiene {len(distintas)} valores distintos de los escritos")
        if len(set(conjuntos.values())) > 1:
            problemas.append("los nodos no ven el mismo conjunto de claves (divergencia)")
        if not problemas or intento == args.reintentos:
            break
        time.sleep(2)  # recién reunificado, un miembro puede estar poniéndose al día

    print(f"{len(escrituras)} escrituras en los CSV: {len(confirmadas)} confirmadas al cliente y "
          f"{len(escrituras) - len(confirmadas)} fallidas.\n")
    print("| Nodo | Confirmadas presentes | Confirmadas que faltan | Fallidas que igual se aplicaron "
          "| Valor distinto |\n|---|---|---|---|---|")
    print("\n".join(filas))
    if getattr(objetivo, "revision", None):
        print("\nRevisión de etcd por miembro: " + ", ".join(f"{n} {r}" for n, r in objetivo.revision.items()))
    if problemas:
        print("\nPROBLEMAS: " + "; ".join(problemas))
        return 1
    espera = f" (tras {2 * (intento - 1)} s de espera)" if intento > 1 else ""
    print(f"\nOK{espera}: todos los nodos tienen todas las escrituras confirmadas, con el valor correcto, "
          "y ven el mismo conjunto de claves.")
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("objetivo", choices=OBJETIVOS)
    p.add_argument("--nodos", help="endpoints separados por comas (s3: URL; etcd: ip:puerto); por defecto, todos")
    p.add_argument("--api", default=META_API, help="URL del servicio de metadatos (objetivo meta)")
    p.add_argument("--etiqueta", default="sonda", help="nombre corto del experimento, por ejemplo e1")
    p.add_argument("--intervalo", type=float, default=0.5, help="segundos entre pedidos de cada tipo")
    p.add_argument("--duracion", type=float, default=0, help="segundos; 0 = hasta Ctrl+C")
    p.add_argument("--timeout", type=float, help="segundos por pedido (por defecto: s3 5, etcd 2, meta 8)")
    p.add_argument("--solo", choices=OPERACIONES, help="hacer un solo tipo de pedido")
    p.add_argument("--bucket", default="sonda", help="bucket de la sonda (s3)")
    p.add_argument("--tam", type=int, default=4096, help="bytes de cada objeto (s3)")
    p.add_argument("--salida", help="CSV; por defecto results/sonda_<etiqueta>_<objetivo>_<fecha>.csv")
    p.add_argument("--informe", type=float, default=2, help="segundos entre líneas de estado; 0 = sin estado")
    p.add_argument("--comprobar", nargs="+", metavar="CSV",
                   help="no sondea: revisa en cada nodo las escrituras registradas en esos CSV")
    p.add_argument("--reintentos", type=int, default=5, help="con --comprobar: intentos, cada 2 s, hasta converger")
    args = p.parse_args()

    args.timeout = args.timeout or TIMEOUT[args.objetivo]
    if args.nodos:
        args.nodos = [n.strip() for n in args.nodos.split(",") if n.strip()]
    elif args.objetivo == "s3":
        import common
        args.nodos = common.NODES
    else:
        args.nodos = [n.strip() for n in ETCD.split(",") if n.strip()]
    clase = OBJETIVOS[args.objetivo]
    if args.comprobar:
        if args.objetivo == "meta":
            sys.exit("--comprobar funciona con s3 y etcd (los documentos del servicio viven en etcd).")
        return comprobar(args, clase)
    return sondear(args, clase)


if __name__ == "__main__":
    sys.exit(main())
