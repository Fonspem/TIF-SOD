# chaos/: inyección de fallas y jornada de caos

Cómo se rompe el sistema a propósito y se vuelve a arreglar. Lo normal es usar `jornada.sh`, que corre cada experimento completo con un solo comando; los otros scripts son las piezas que usa.

| Archivo | Qué hace | Ejemplo |
|---|---|---|
| `jornada.sh` | **Un experimento de punta a punta**: controla que todo esté bien, prende las sondas, inyecta la falla, la revierte (también si se corta con Ctrl+C), espera a que el clúster vuelva, verifica las 1.000 actas y corre el análisis. Guarda todo en `results/` | `chaos/jornada.sh e3` |
| `e1_caida_nodo.sh` | **E1**: apaga una VM de golpe (como un corte de luz) o de forma ordenada, y la vuelve a prender | `chaos/e1_caida_nodo.sh apagar vm4` |
| `e3_particion.sh` | **E3**: aísla una VM de las otras tres con iptables, y la reunifica | `chaos/e3_particion.sh aislar vm3` |
| `e4_netem.sh` | **E4**: agrega demora y pérdida de paquetes a la red de las VM con tc netem, y la saca | `chaos/e4_netem.sh aplicar` |
| `e4-netem.yaml` | La misma falla de E4 escrita para Chaos Mesh (no se usó: queda como referencia) | — |

## Los experimentos de `jornada.sh`

| Comando | Falla | Dura |
|---|---|---|
| `chaos/jornada.sh estado` | Ninguna: solo los controles de estado estable | 10 s |
| `chaos/jornada.sh e4` | Red degradada: 200 ms de demora y 5 % de pérdida en las 4 VM | ~7 min |
| `chaos/jornada.sh e3` | Partición: vm3 aislada de las otras tres durante 60 s | ~4 min |
| `chaos/jornada.sh e1-uno` | vm4 apagada de golpe durante 150 s | ~5 min |
| `chaos/jornada.sh e1-dos` | vm4 y vm3 apagadas de golpe | ~5 min |
| `APAGADO=ordenado chaos/jornada.sh e1-dos` | E1-bis: las dos apagadas de forma ordenada | ~5 min |
| `T_FALLA=300 chaos/jornada.sh e1-dos` | E1-bis: de golpe, durante 5 minutos | ~8 min |

Antes de correr un experimento, leer [`docs/runbook.md`](../docs/runbook.md): criterios para abortar y cómo revertir a mano cada falla. Los resultados de cada corrida están explicados en [`docs/postmortems/`](../docs/postmortems/).

Los scripts sueltos escriben sus eventos en `results/eN_eventos.csv`; para que no se mezclen con los de la jornada, se puede cambiar con `EVENTOS=/tmp/otro.csv` (la demo lo hace así).
