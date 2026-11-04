"""Pruebas del servicio de metadatos contra un clúster etcd real de 3 miembros.

Levantan etcd en 127.0.0.1 (puertos 2379, 22379 y 32379). Requieren el binario
de etcd en el PATH o en la variable ETCD_BIN:

    ETCD_BIN=/ruta/a/etcd pytest -q metadata-service/tests
"""
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time

import pytest
import requests

MIEMBROS = {"n1": (2379, 2380), "n2": (22379, 22380), "n3": (32379, 32380)}
CLUSTER = ",".join(f"{n}=http://127.0.0.1:{p}" for n, (_, p) in MIEMBROS.items())

os.environ["ETCD"] = ",".join(f"127.0.0.1:{c}" for c, _ in MIEMBROS.values())
os.environ["LOCK_TTL"] = "3"
os.environ["ETCD_TIMEOUT"] = "1"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import app as servicio  # noqa: E402


class Cluster:
    def __init__(self, binario, directorio):
        self.binario, self.dir, self.procs = binario, directorio, {}

    def iniciar(self, nombre, estado="new"):
        cliente, par = MIEMBROS[nombre]
        log = open(os.path.join(self.dir, f"{nombre}.log"), "ab")
        self.procs[nombre] = subprocess.Popen([
            self.binario, "--name", nombre, "--data-dir", os.path.join(self.dir, nombre),
            "--listen-client-urls", f"http://127.0.0.1:{cliente}",
            "--advertise-client-urls", f"http://127.0.0.1:{cliente}",
            "--listen-peer-urls", f"http://127.0.0.1:{par}",
            "--initial-advertise-peer-urls", f"http://127.0.0.1:{par}",
            "--initial-cluster", CLUSTER, "--initial-cluster-state", estado,
            "--initial-cluster-token", "pruebas", "--log-level", "error",
        ], stdout=log, stderr=log)

    def matar(self, nombre):
        self.procs[nombre].send_signal(signal.SIGKILL)
        self.procs[nombre].wait()

    def esperar_quorum(self, segundos=20):
        fin = time.time() + segundos
        while time.time() < fin:
            for cliente, _ in MIEMBROS.values():
                try:
                    r = requests.post(f"http://127.0.0.1:{cliente}/v3/kv/range",
                                      json={"key": "eA=="}, timeout=0.5)
                    if r.ok:
                        return
                except requests.RequestException:
                    pass
            time.sleep(0.2)
        raise RuntimeError("el clúster no formó quórum")

    def apagar(self):
        for p in self.procs.values():
            if p.poll() is None:
                p.kill()


@pytest.fixture(scope="session")
def cluster():
    binario = os.environ.get("ETCD_BIN") or shutil.which("etcd")
    if not binario:
        pytest.skip("no se encontró el binario de etcd")
    directorio = tempfile.mkdtemp(prefix="etcd-pruebas-")
    c = Cluster(binario, directorio)
    for n in MIEMBROS:
        c.iniciar(n)
    c.esperar_quorum()
    yield c
    c.apagar()
    shutil.rmtree(directorio, ignore_errors=True)


@pytest.fixture
def api(cluster):
    return servicio.app.test_client()


def test_alta_y_consulta(api):
    assert api.post("/docs/acta-0001", json={"sha256": "abc", "bytes": 10}).status_code == 201
    assert api.post("/docs/acta-0001", json={}).status_code == 409
    r = api.get("/docs/acta-0001")
    assert r.status_code == 200 and r.json["estado"] == "borrador"
    assert api.get("/docs/no-existe").status_code == 404


def test_un_solo_cliente_obtiene_el_bloqueo(api):
    api.post("/docs/acta-0002", json={})
    codigos = []

    def pedir(i):
        codigos.append(servicio.app.test_client().post("/docs/acta-0002/lock", json={"owner": f"c{i}"}).status_code)

    hilos = [threading.Thread(target=pedir, args=(i,)) for i in range(10)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    assert sorted(codigos) == [200] + [409] * 9


def test_cambio_de_estado_con_bloqueo(api):
    api.post("/docs/acta-0003", json={})
    token = api.post("/docs/acta-0003/lock", json={"owner": "A"}).json["token"]
    assert api.put("/docs/acta-0003/state", json={"estado": "firmada"}).status_code == 400  # sin token
    assert api.put("/docs/acta-0003/state", json={"estado": "archivada", "token": token}).status_code == 400
    assert api.put("/docs/acta-0003/state", json={"estado": "firmada", "token": token}).status_code == 200
    assert api.put("/docs/acta-0003/state", json={"estado": "archivada", "token": token}).status_code == 200
    assert api.get("/docs/acta-0003").json["estado"] == "archivada"
    assert api.delete("/docs/acta-0003/lock", json={"token": token + 1}).status_code == 409
    assert api.delete("/docs/acta-0003/lock", json={"token": token}).status_code == 200
    assert api.post("/docs/acta-0003/lock", json={"owner": "B"}).status_code == 200


def test_fencing_rechaza_al_duenio_viejo(api):
    api.post("/docs/acta-0004", json={})
    viejo = api.post("/docs/acta-0004/lock", json={"owner": "A"}).json["token"]
    time.sleep(servicio.LOCK_TTL + 1.5)  # A queda "pausado" sin renovar y su lease vence
    nuevo = api.post("/docs/acta-0004/lock", json={"owner": "B"})
    assert nuevo.status_code == 200 and nuevo.json["token"] > viejo
    assert api.put("/docs/acta-0004/state", json={"estado": "firmada", "token": viejo}).status_code == 409
    assert api.put("/docs/acta-0004/state", json={"estado": "firmada", "token": nuevo.json["token"]}).status_code == 200


def test_renovar_mantiene_el_bloqueo(api):
    api.post("/docs/acta-0005", json={})
    lock = api.post("/docs/acta-0005/lock", json={"owner": "A"}).json
    for _ in range(4):  # 4 s con TTL de 3 s
        time.sleep(1)
        assert api.post("/docs/acta-0005/lock/refresh", json={"lease": lock["lease"]}).status_code == 200
        assert api.post("/docs/acta-0005/lock", json={"owner": "B"}).status_code == 409


def test_sigue_andando_si_cae_un_miembro(api, cluster):
    cluster.matar("n1")
    try:
        assert api.post("/docs/acta-0006", json={}).status_code == 201
        assert api.get("/health").status_code == 200
    finally:
        cluster.iniciar("n1", estado="existing")
        cluster.esperar_quorum()


def test_sin_quorum_responde_503(api, cluster):
    cluster.matar("n2")
    cluster.matar("n3")
    try:
        assert api.get("/health").status_code == 503
        assert api.post("/docs/acta-0007", json={}).status_code == 503
    finally:
        cluster.iniciar("n2", estado="existing")
        cluster.iniciar("n3", estado="existing")
        cluster.esperar_quorum()
    assert api.get("/health").status_code == 200
