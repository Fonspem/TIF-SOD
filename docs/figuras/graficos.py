"""Gráficos del informe (PNG estáticos): E2 con stop y tiempos de recuperación."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

SUP, TXT, TXT2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
AZUL, NARANJA = "#2a78d6", "#eb6834"
DPI = 200
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "text.color": TXT,
                     "axes.labelcolor": TXT2, "xtick.color": TXT2, "ytick.color": TXT2})


def ejes(fig, ax):
    fig.patch.set_facecolor(SUP); ax.set_facecolor(SUP)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color(GRID); ax.spines["bottom"].set_linewidth(1)
    ax.tick_params(length=0)


def barra(ax, x, ancho, alto, color, horizontal=False, radio_px=4):
    """Barra con el extremo de datos redondeado (4 px) y la base recta."""
    fig = ax.figure
    fig.canvas.draw()
    inv = ax.transData.inverted()
    p0 = inv.transform((0, 0)); p1 = inv.transform((radio_px, radio_px))
    rx, ry = abs(p1[0] - p0[0]), abs(p1[1] - p0[1])
    if horizontal:   # x = posición en y (centro), alto = largo en x
        y, w, h = x - ancho / 2, alto, ancho
        r = min(rx, w / 2)
        ax.add_patch(FancyBboxPatch((0, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}",
                                    mutation_aspect=ry / rx, fc=color, ec="none"))
        ax.add_patch(Rectangle((0, y), max(w - r, 0), h, fc=color, ec="none"))
    else:
        xi, w, h = x - ancho / 2, ancho, alto
        r = min(ry, h / 2)
        ax.add_patch(FancyBboxPatch((xi, 0), w, h, boxstyle=f"round,pad=0,rounding_size={rx}",
                                    mutation_aspect=ry / rx, fc=color, ec="none"))
        ax.add_patch(Rectangle((xi, 0), w, max(h - r, 0), fc=color, ec="none"))


# 1. E2 con systemctl stop: 10 corridas (salida de leader_election.py, 12/11/2026)
corridas = list(range(1, 11))
cayo = ["vm3", "vm2", "vm1", "vm3", "vm2", "vm1", "vm3", "vm2", "vm1", "vm3"]
lider = [78, 63, 56, 36, 62, 56, 63, 59, 87, 61]
escritura = [94, 119, 76, 68, 74, 72, 81, 74, 104, 82]
fig, ax = plt.subplots(figsize=(8, 4), dpi=DPI)
ejes(fig, ax)
ax.set_xlim(0.4, 10.6); ax.set_ylim(0, 130)
ax.set_yticks([0, 25, 50, 75, 100, 125]); ax.set_ylabel("milisegundos")
ax.yaxis.grid(True, color=GRID, linewidth=1); ax.set_axisbelow(True)
px = (ax.transData.transform((1, 0))[0] - ax.transData.transform((0, 0))[0])  # px por unidad x
ancho = 22 / px; hueco = 2 / px
for x, a, b in zip(corridas, lider, escritura):
    barra(ax, x - (ancho + hueco) / 2, ancho, a, AZUL)
    barra(ax, x + (ancho + hueco) / 2, ancho, b, NARANJA)
ax.set_xticks(corridas, [f"{c}\ncayó {v}" for c, v in zip(corridas, cayo)])
fig.suptitle("E2 con systemctl stop: tiempos de cada corrida", x=0.06, ha="left", fontsize=11, color=TXT, y=0.98)
fig.text(0.06, 0.905, "Mediana: 62 ms hasta el nuevo líder y 78 ms hasta la primera escritura (10 corridas, 12/11/2026)",
         ha="left", fontsize=8.5, color=TXT2)
from matplotlib.lines import Line2D
ley = [Line2D([0], [0], marker="s", color=SUP, markerfacecolor=c, markersize=8, label=t)
       for c, t in ((AZUL, "hasta el nuevo líder"), (NARANJA, "hasta la primera escritura aceptada"))]
ax.legend(handles=ley, loc="upper left", bbox_to_anchor=(-0.03, 1.12), ncol=2, frameon=False, fontsize=8.5,
          handletextpad=0.3, columnspacing=1.5)
fig.subplots_adjust(left=0.08, right=0.98, top=0.8, bottom=0.17)
fig.savefig("e2-stop-corridas.png", facecolor=SUP)
plt.close(fig)

# 2. Tiempo hasta que la VM vuelve a funcionar (minutos)
casos = ["Incidente de vm3: reinicio a mano\n(11:28 a 15:48 del 12/11)",
         "VM congelada a propósito,\ncon watchdog (prueba)",
         "Pánico del kernel, con\nkernel.panic=10 de k3s (prueba)"]
minutos = [260, 35 / 60, 18 / 60]
textos = ["4 h 20 min", "35 s", "18 s"]
fig, ax = plt.subplots(figsize=(8, 2.8), dpi=DPI)
ejes(fig, ax)
ax.set_xlim(0, 300); ax.set_ylim(-0.6, 2.6)
ax.set_xticks([0, 60, 120, 180, 240], ["0", "1 h", "2 h", "3 h", "4 h"])
ax.xaxis.grid(True, color=GRID, linewidth=1); ax.set_axisbelow(True)
ax.spines["bottom"].set_visible(False)
py = (ax.transData.transform((0, 1))[1] - ax.transData.transform((0, 0))[1])
alto = 20 / py
for i, (m, t) in enumerate(zip(minutos, textos)):
    y = 2 - i
    barra(ax, y, alto, max(m, 0.0001), AZUL, horizontal=True)
    ax.text(m + 4, y, t, va="center", ha="left", fontsize=9, color=TXT)
ax.set_yticks([2, 1, 0], casos)
fig.suptitle("Tiempo hasta que la VM vuelve a funcionar", x=0.02, ha="left", fontsize=11, y=0.97)
fig.text(0.02, 0.86, "Desde que deja de responder hasta que vuelve a contestar", ha="left", fontsize=8.5, color=TXT2)
fig.subplots_adjust(left=0.3, right=0.97, top=0.78, bottom=0.12)
fig.savefig("recuperacion-vm.png", facecolor=SUP)
plt.close(fig)
print("listo")
