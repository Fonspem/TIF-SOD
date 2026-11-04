"""Cálculos compartidos por la sonda (probe.py) y el análisis (analyze.py)."""


def percentil(valores, p):
    """Percentil p (de 0 a 100) con interpolación lineal; None si no hay valores."""
    v = sorted(valores)
    if not v:
        return None
    k = (len(v) - 1) * p / 100
    i = int(k)
    return v[i] + (v[min(i + 1, len(v) - 1)] - v[i]) * (k - i)


def cortes(pedidos):
    """Rachas sin servicio en una serie de (t, ok) ordenada por t.

    Cada corte va desde el primer pedido fallido de la racha hasta el siguiente
    pedido que salió bien. Devuelve una lista de (inicio, fin, fallas); fin es
    None si la serie termina sin recuperarse.
    """
    res, inicio, fallas = [], None, 0
    for t, ok in pedidos:
        if not ok:
            if inicio is None:
                inicio, fallas = t, 0
            fallas += 1
        elif inicio is not None:
            res.append((inicio, t, fallas))
            inicio = None
    if inicio is not None:
        res.append((inicio, None, fallas))
    return res
