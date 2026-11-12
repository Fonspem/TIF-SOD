# Figuras del informe

| Archivo | Cómo se genera |
|---|---|
| `arquitectura.png` | `dot -Tpng -Gdpi=170 arquitectura.dot -o arquitectura.png` (Graphviz) |
| `e2-stop-corridas.png` y `recuperacion-vm.png` | `python graficos.py` (matplotlib); los datos están dentro del script y salen de las salidas de los experimentos del 12/11/2026 |
