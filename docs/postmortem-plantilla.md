# Post-mortem: EN · [nombre del experimento]

<!--
Cómo usar esta plantilla:
- Copiarla a docs/postmortems/eN.md (por ejemplo, docs/postmortems/e1.md) y completar cada sección.
- Se escribe al terminar el experimento, con los datos todavía frescos, aunque se haya abortado.
- Sin culpas: se describe qué pasó y por qué, no quién se equivocó. Un error de operación
  también es un dato: dice qué paso del runbook hay que hacer más claro o más seguro.
- Los números salen de analyze.py (results/) y de Grafana, no de la memoria.
-->

| Dato | Valor |
|---|---|
| Fecha y hora | [AAAA-MM-DD, de HH:MM a HH:MM] |
| Quién operó / quién observó | [nombre, rol] / [nombre, rol] |
| Corrida | [N de M] |
| Versión del repositorio | [salida de `git rev-parse --short HEAD`] |
| Resultado | [Hipótesis confirmada / refutada / confirmada en parte] |

## Resumen

[Dos o tres oraciones: qué falla se inyectó, qué pasó y si se confirmó la hipótesis.]

## Hipótesis y estado estable

- **Hipótesis** (la de la tabla del Paso 6): [...]
- **Métrica de estado estable y umbral:** [por ejemplo: lecturas y escrituras de la sonda sin errores y p95 menor a X ms]
- **Valor antes de la falla:** [tramo «antes» de `analyze.py sonda`]

## Inyección

- **Qué y cómo:** [comando exacto, por ejemplo `../chaos/e1_caida_nodo.sh apagar vm4`]
- **Inicio y reversión:** [horas de `results/eN_eventos.csv`]
- **Radio de impacto previsto:** [qué componentes debían verse afectados y cuáles no]

## Cronología

| Hora | Qué pasó | Fuente |
|---|---|---|
| [HH:MM:SS] | [estado estable confirmado] | [runbook, sección 2] |
| [HH:MM:SS] | [inyección] | [eventos] |
| [HH:MM:SS] | [primer error de la sonda] | [sonda] |
| [HH:MM:SS] | [lo que se vio en Grafana] | [Grafana] |
| [HH:MM:SS] | [reversión] | [eventos] |
| [HH:MM:SS] | [vuelta al estado estable] | [sonda y Grafana] |

## Impacto medido

| Indicador | Antes | Durante | Después |
|---|---|---|---|
| Disponibilidad de lectura | | | |
| Disponibilidad de escritura | | | |
| Latencia p50 / p95 | | | |
| Corte más largo | | | |

- **Tiempo hasta el primer error:** [s]
- **Tiempo de recuperación** (de la reversión al estado estable): [s]
- **Integridad:** [salida de `verify.py`, por ejemplo `OK: 1000 / 1000  fallas: 0`]

## Análisis

- **¿Se confirmó la hipótesis?** [Sí / No / En parte, y por qué]
- **Diferencias con lo esperado y su explicación:** [con lo que dice el diseño: quórum de MinIO, Raft, lease, red de gestión de Vagrant, etc.]
- **Qué anduvo bien:** [...]
- **Qué anduvo mal o sorprendió:** [...]

## Acciones

| Acción | Responsable | Para cuándo | Estado |
|---|---|---|---|
| [mejora al sistema, al runbook o a la medición] | [rol] | [fecha] | [pendiente / hecha] |

## Evidencias

- Datos: [`results/eN_*.csv`]
- Figura: [`results/figuras/eN.png`]
- Capturas de Grafana y de la terminal: [rutas o enlaces]
