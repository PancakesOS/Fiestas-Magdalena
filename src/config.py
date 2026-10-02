"""Rutas, claves geográficas y constantes compartidas por scripts y notebooks."""

from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

DIR_DATOS = RAIZ / "datos"
DIR_RAW = DIR_DATOS / "raw"
DIR_PROCESSED = DIR_DATOS / "processed"
DIR_MANUAL = DIR_DATOS / "manual"
DIR_FIGURAS = RAIZ / "outputs" / "figuras"
DIR_TABLAS = RAIZ / "outputs" / "tablas"

USER_AGENT = "SahuarisResearch/0.1 (investigacion Fiestas de Magdalena)"

CVE_ENT_SONORA = "26"
CVE_MUN_MAGDALENA = "036"
CVE_LOC_CABECERA = "0001"

# Municipios de Sonora de donde salen las rutas de peregrinación documentadas en prensa.
MUNICIPIOS_ORIGEN = {
    "002": "Agua Prieta",
    "019": "Cananea",
    "022": "Cucurpe",
    "035": "Ímuris",
    "043": "Nogales",
    "058": "Santa Ana",
}

# Ventana de las Fiestas de Octubre usada en todo el análisis (26 sept - 6 oct).
FIESTAS_INICIO_MMDD = "09-26"
FIESTAS_FIN_MMDD = "10-06"
DIA_CENTRAL_MMDD = "10-04"

# Censos y conteos del INEGI: resultados por localidad (ITER) de Sonora.
URLS_ITER = {
    2000: "https://www.inegi.org.mx/contenidos/programas/ccpv/2000/datosabiertos/cgpv2000_iter_26_csv.zip",
    2005: "https://www.inegi.org.mx/contenidos/programas/ccpv/2005/datosabiertos/cpv2005_iter_26_csv.zip",
    2010: "https://www.inegi.org.mx/contenidos/programas/ccpv/2010/datosabiertos/iter_26_2010_csv.zip",
    2020: "https://www.inegi.org.mx/contenidos/programas/ccpv/2020/datosabiertos/iter/iter_26_cpv2020_csv.zip",
}

URL_DENUE_SONORA = "https://www.inegi.org.mx/contenidos/masiva/denue/denue_26_csv.zip"

URL_COESPO_MAGDALENA = (
    "https://coespo.sonora.gob.mx/documentos/Proyecciones-Municipales-2025-2040/Magdalena.pdf"
)

URL_OPEN_METEO = "https://archive-api.open-meteo.com/v1/archive"
URL_OSRM = "https://router.project-osrm.org/route/v1/driving"
URL_WIKIMEDIA_PAGEVIEWS = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"
URL_WAYBACK = "https://archive.org/wayback/available"

# Artículos de Wikipedia cuya audiencia se usa como termómetro de atención pública.
ARTICULOS_WIKIPEDIA = [
    ("es.wikipedia", "Magdalena_de_Kino"),
    ("es.wikipedia", "Magdalena_(Sonora)"),
    ("en.wikipedia", "Magdalena_de_Kino"),
    ("es.wikipedia", "Eusebio_Francisco_Kino"),
]
WIKIPEDIA_INICIO = "20150701"
