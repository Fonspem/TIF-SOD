# k8s/: MinIO distribuido en Kubernetes

`minio.yaml` despliega MinIO con 4 pods, uno por VM, cada uno con su disco (`/mnt/minio`). Con 4 discos MinIO usa codificación de borrado EC 2+2: guarda cada objeto en 2 partes de datos y 2 de paridad, así que ocupa el doble y puede leer con 2 discos y escribir con 3.

Cada pod publica el puerto 9000 en su propia VM (`hostPort`): los scripts hablan con cada nodo por separado y, si uno no responde, pasan al siguiente.

```bash
kubectl create namespace minio
kubectl -n minio create secret generic minio-creds \
  --from-literal=MINIO_ROOT_USER=admin --from-literal=MINIO_ROOT_PASSWORD='<contraseña>'
kubectl apply -f k8s/minio.yaml
kubectl -n minio get pods -o wide      # 4 pods Running, uno por VM
```

La imagen es `pgsty/minio`, el fork comunitario: desde el 24/09/2026 las imágenes oficiales ya no se pueden bajar sin cuenta.
