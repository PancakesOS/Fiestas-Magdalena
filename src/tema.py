"""Identidad visual de Sahuaris para Plotly y exportación de figuras.

Paleta del manual de marca (Kit_Articulo/PROMPT_FOTOS_TEMPLATE.md). El morado
#4A3458 se reserva para texto y contornos: como color de dato se lee gris.
Regla de uso: una sola serie protagonista en magenta, el resto en neutros, y
el teal/dorado solo cuando hay una segunda categoría que nombrar.
"""

import plotly.graph_objects as go
import plotly.io as pio

from src import config

FONDO = "#FDF8F5"
TEXTO = "#2D2436"
TEXTO_SUAVE = "#6B5F73"
PROTAGONISTA = "#D81E5B"
SECUNDARIO = "#0CA4A5"
TERCIARIO = "#EAA134"
CONTORNO = "#4A3458"
CUADRICULA = "#E9DFD5"
NEUTRO = "#CFC3B8"
FUENTE = "DM Sans, Helvetica, Arial, sans-serif"

_FONT_LINK = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&display=swap" '
    'rel="stylesheet">'
)

pio.templates["sahuaris"] = go.layout.Template(
    layout=dict(
        font=dict(family=FUENTE, color=TEXTO, size=13),
        paper_bgcolor=FONDO,
        plot_bgcolor=FONDO,
        colorway=[PROTAGONISTA, SECUNDARIO, TERCIARIO, CONTORNO, NEUTRO],
        title=dict(x=0.02, xanchor="left", font=dict(size=20, color=TEXTO)),
        xaxis=dict(showgrid=False, zeroline=False, linecolor=NEUTRO, ticks="outside", tickcolor=NEUTRO),
        yaxis=dict(gridcolor=CUADRICULA, zeroline=False, linecolor=NEUTRO),
        hoverlabel=dict(bgcolor="white", bordercolor=NEUTRO, font=dict(family=FUENTE, color=TEXTO)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, bgcolor="rgba(0,0,0,0)"),
        margin=dict(t=125, l=20, r=30, b=95),
    )
)
pio.templates.default = "plotly_white+sahuaris"


def titulo(principal: str, subtitulo: str = "") -> dict:
    texto = f"<b>{principal}</b>"
    if subtitulo:
        texto += f"<br><span style='font-size:13px;color:{TEXTO_SUAVE}'>{subtitulo}</span>"
    return dict(text=texto)


def nota_fuente(fig: go.Figure, texto: str) -> go.Figure:
    """Pie de figura con la fuente, alineado a la izquierda."""
    fig.add_annotation(
        text=texto,
        xref="paper",
        yref="paper",
        x=0,
        y=0,
        yshift=-58,
        xanchor="left",
        yanchor="top",
        showarrow=False,
        align="left",
        font=dict(size=11, color=TEXTO_SUAVE),
    )
    return fig


def guardar(fig: go.Figure, nombre: str, alto: int | None = None, ancho: int = 900) -> None:
    """Exporta a outputs/figuras/{nombre}.html (interactiva) y .png (2x, estática)."""
    config.DIR_FIGURAS.mkdir(parents=True, exist_ok=True)
    alto = alto or fig.layout.height or 520
    ruta_html = config.DIR_FIGURAS / f"{nombre}.html"
    fig.write_html(ruta_html, include_plotlyjs="cdn", full_html=True, config={"displaylogo": False})
    contenido = ruta_html.read_text(encoding="utf-8").replace("<head>", f"<head>{_FONT_LINK}", 1)
    ruta_html.write_text(contenido, encoding="utf-8")
    fig.write_image(config.DIR_FIGURAS / f"{nombre}.png", scale=2, width=ancho, height=alto)


def mostrar(fig: go.Figure, nombre: str, alto: int | None = None, ancho: int = 900):
    """Guarda la figura y la devuelve como PNG para el notebook.

    GitHub no ejecuta el JavaScript de Plotly al mostrar un .ipynb, así que la
    salida guardada en el notebook es la imagen; la versión interactiva queda en
    outputs/figuras/{nombre}.html.
    """
    from IPython.display import Image

    guardar(fig, nombre, alto=alto, ancho=ancho)
    print(f"Interactiva: outputs/figuras/{nombre}.html")
    return Image(filename=str(config.DIR_FIGURAS / f"{nombre}.png"), width=ancho)
