"""Servicio de metadatos del TIF (Propuesta C).

Guarda en etcd el estado de cada documento (borrador -> firmada -> archivada) e
impide que dos clientes lo modifiquen a la vez con un bloqueo atado a un lease.

La create_revision de la clave del bloqueo funciona como fencing token: todo
cambio de estado es una transacción que exige que el bloqueo siga existiendo con
ese mismo token. Si el lease venció y otro cliente tomó el bloqueo, la escritura
del cliente viejo se rechaza aunque él crea que todavía es el dueño.

Habla con etcd por su API HTTP/JSON a través de etcd3gw. Conoce los tres
miembros y, si uno no responde, prueba con el siguiente. Si ninguno responde o
no hay quórum, contesta 503: el servicio prefiere consistencia a disponibilidad.
"""
import base64
import json
import os

import etcd3gw
from etcd3gw import exceptions as etcd_exc
from etcd3gw.lease import Lease
from flask import Flask, jsonify, request

ENDPOINTS = [e.strip() for e in os.environ.get(
    "ETCD", "192.168.56.11:2379,192.168.56.12:2379,192.168.56.13:2379").split(",") if e.strip()]
LOCK_TTL = int(os.environ.get("LOCK_TTL", "15"))          # segundos
ETCD_TIMEOUT = float(os.environ.get("ETCD_TIMEOUT", "2"))  # segundos por pedido a etcd
TRANSICIONES = {"borrador": {"firmada"}, "firmada": {"archivada"}, "archivada": set()}

app = Flask(__name__)
_preferido = 0  # índice del último miembro de etcd que respondió


class SinEtcd(Exception):
    """Ningún miembro de etcd respondió o no hay quórum."""


def b64(texto):
    return base64.b64encode(texto.encode()).decode()


def clave_lock(doc):
    return f"/locks/{doc}"


def clave_doc(doc):
    return f"/docs/{doc}"


def etcd(operacion):
    """Ejecuta operacion(cliente) contra el primer miembro que responda.

    Empieza por el último que anduvo. Ojo: un pedido que venció por timeout
    pudo haberse aplicado igual; las operaciones de abajo están armadas para que
    reintentarlas no rompa la exclusión mutua (a lo sumo, un bloqueo queda
    tomado hasta que vence su lease).
    """
    global _preferido
    ultimo_error = None
    for i in range(len(ENDPOINTS)):
        idx = (_preferido + i) % len(ENDPOINTS)
        host, port = ENDPOINTS[idx].rsplit(":", 1)
        cliente = etcd3gw.client(host=host, port=int(port), timeout=ETCD_TIMEOUT)
        try:
            resultado = operacion(cliente)
        except etcd_exc.Etcd3Exception as e:
            ultimo_error = e
            continue
        _preferido = idx
        return resultado
    raise SinEtcd(str(ultimo_error))


def transaccion(cliente, compare, success):
    """Devuelve (se_aplicó, respuesta). etcd omite 'succeeded' cuando es falso."""
    r = cliente.transaction({"compare": compare, "success": success, "failure": []})
    return bool(r.get("succeeded", False)), r


def token_del_cuerpo():
    try:
        return int((request.get_json(silent=True) or {}).get("token", 0))
    except (TypeError, ValueError):
        return 0


@app.errorhandler(SinEtcd)
def sin_etcd(e):
    return jsonify(error="etcd no disponible o sin quórum", detalle=str(e)[:200]), 503


@app.get("/health")
def salud():
    # Lectura linealizable: sólo responde si el miembro está en la mayoría.
    etcd(lambda c: c.get("/salud"))
    return jsonify(ok=True), 200


@app.post("/docs/<doc>")
def alta(doc):
    """Registra un documento nuevo en estado borrador (sin bloqueo: la creación es atómica)."""
    datos = request.get_json(silent=True) or {}
    meta = {"estado": "borrador", **{k: datos[k] for k in ("sha256", "bytes", "objeto") if k in datos}}

    def op(c):
        ok, _ = transaccion(
            c,
            compare=[{"key": b64(clave_doc(doc)), "result": "EQUAL", "target": "VERSION", "version": 0}],
            success=[{"request_put": {"key": b64(clave_doc(doc)), "value": b64(json.dumps(meta))}}],
        )
        return ok

    if etcd(op):
        return jsonify(meta), 201
    return jsonify(error="el documento ya existe"), 409


@app.get("/docs/<doc>")
def consulta(doc):
    valores = etcd(lambda c: c.get(clave_doc(doc)))
    if not valores:
        return jsonify(error="no existe"), 404
    return jsonify(json.loads(valores[0])), 200


@app.post("/docs/<doc>/lock")
def tomar_bloqueo(doc):
    """Crea /locks/<doc> sólo si no existe, atado a un lease de LOCK_TTL segundos."""
    duenio = str((request.get_json(silent=True) or {}).get("owner", "anonimo"))

    def op(c):
        lease = c.lease(LOCK_TTL)
        ok, r = transaccion(
            c,
            compare=[{"key": b64(clave_lock(doc)), "result": "EQUAL", "target": "CREATE", "create_revision": 0}],
            success=[{"request_put": {"key": b64(clave_lock(doc)), "value": b64(duenio), "lease": lease.id}}],
        )
        if not ok:
            lease.revoke()
            return None
        # La clave se creó en esta revisión: es su create_revision, el fencing token.
        return {"token": int(r["header"]["revision"]), "lease": str(lease.id), "ttl": LOCK_TTL}

    res = etcd(op)
    if res is None:
        return jsonify(error="documento bloqueado por otro cliente"), 409
    return jsonify(res), 200


@app.post("/docs/<doc>/lock/refresh")
def renovar_bloqueo(doc):
    """Renueva el lease. El cliente debe llamarlo cada TTL/3 mientras edita."""
    try:
        lease_id = int((request.get_json(silent=True) or {})["lease"])
    except (KeyError, TypeError, ValueError):
        return jsonify(error="falta el lease"), 400
    ttl = etcd(lambda c: Lease(lease_id, client=c).refresh())
    if ttl <= 0:
        return jsonify(error="el lease ya venció"), 409
    return jsonify(ttl=ttl), 200


@app.put("/docs/<doc>/state")
def cambiar_estado(doc):
    cuerpo = request.get_json(silent=True) or {}
    nuevo, token = cuerpo.get("estado"), token_del_cuerpo()
    if token <= 0:
        return jsonify(error="falta el token del bloqueo"), 400

    def op(c):
        actual = c.get(clave_doc(doc), metadata=True)
        if not actual:
            return 404, {"error": "no existe"}
        valor, meta = actual[0]
        datos = json.loads(valor)
        if nuevo not in TRANSICIONES.get(datos.get("estado"), set()):
            return 400, {"error": f"transición inválida: {datos.get('estado')} -> {nuevo}"}
        datos.update(estado=nuevo, token=token)
        ok, _ = transaccion(
            c,
            compare=[
                # Fencing: el bloqueo sigue existiendo y es el mismo que obtuvo este cliente.
                {"key": b64(clave_lock(doc)), "result": "EQUAL", "target": "CREATE", "create_revision": token},
                # Y nadie cambió el documento desde que lo leímos.
                {"key": b64(clave_doc(doc)), "result": "EQUAL", "target": "MOD",
                 "mod_revision": int(meta["mod_revision"])},
            ],
            success=[{"request_put": {"key": b64(clave_doc(doc)), "value": b64(json.dumps(datos))}}],
        )
        if ok:
            return 200, datos
        return 409, {"error": "bloqueo perdido o token vencido"}

    codigo, respuesta = etcd(op)
    return jsonify(respuesta), codigo


@app.delete("/docs/<doc>/lock")
def liberar_bloqueo(doc):
    token = token_del_cuerpo()
    if token <= 0:
        return jsonify(error="falta el token del bloqueo"), 400

    def op(c):
        actual = c.get(clave_lock(doc), metadata=True)
        ok, _ = transaccion(
            c,
            compare=[{"key": b64(clave_lock(doc)), "result": "EQUAL", "target": "CREATE", "create_revision": token}],
            success=[{"request_delete_range": {"key": b64(clave_lock(doc))}}],
        )
        if ok and actual and actual[0][1].get("lease"):
            Lease(int(actual[0][1]["lease"]), client=c).revoke()
        return ok

    if etcd(op):
        return jsonify(ok=True), 200
    return jsonify(error="no sos el dueño del bloqueo o ya venció"), 409


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), threaded=True)
