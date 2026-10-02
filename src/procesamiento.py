"""Lectura y homologación de las fuentes crudas de datos/raw/.

Cada función devuelve un DataFrame limpio con nombres de columna en español y
tipos correctos. Los notebooks importan de aquí; `construir_tablas()` escribe las
versiones procesadas a datos/processed/.
"""

import json
import re
from functools import lru_cache

import pandas as pd

from src import config

# --- Censos (ITER) -----------------------------------------------------------

_ARCHIVO_ITER = {
    2000: "cgpv2000_iter_26.csv",
    2005: "cpv2005_iter_26.csv",
    2010: "iter_26_cpv2010.csv",
    2020: "conjunto_de_datos_iter_26CSV20.csv",
}

# Cada levantamiento nombra distinto las mismas variables.
_COLUMNAS_ITER = {
    "pobtot": ["pobtot", "p_total"],
    "vivtot": ["vivtot"],
    "viv_habitadas": ["tvivparhab"],
    "viv_deshabitadas": ["vivpar_des"],
    "viv_uso_temporal": ["vivpar_ut"],
}


def _dms_a_decimal(valor: str | float, negativo: bool) -> float:
    """Convierte coordenadas del ITER a grados decimales.

    2000-2010 usan un entero compacto GGGMMSS ("1105803" = 110°58'03");
    2020 usa texto DMS (110°58'09.856" W).
    """
    if pd.isna(valor):
        return float("nan")
    texto = str(valor).strip()
    partes = re.findall(r"[\d.]+", texto)
    if len(partes) >= 3:
        grados, minutos, segundos = (float(p) for p in partes[:3])
    else:
        texto = texto.zfill(7) if negativo else texto.zfill(6)
        grados, minutos, segundos = float(texto[:-4]), float(texto[-4:-2]), float(texto[-2:])
    decimal = grados + minutos / 60 + segundos / 3600
    return -decimal if negativo else decimal


def _a_numero(serie: pd.Series) -> pd.Series:
    """El INEGI marca con '*' o 'N/D' los valores reservados por confidencialidad."""
    return pd.to_numeric(serie.replace({"*": None, "N/D": None}), errors="coerce")


@lru_cache(maxsize=None)
def leer_iter(anio: int) -> pd.DataFrame:
    """Resultados por localidad de Sonora para un levantamiento, con columnas homologadas."""
    ruta = next((config.DIR_RAW / "inegi").rglob(_ARCHIVO_ITER[anio]))
    df = pd.read_csv(ruta, encoding="utf-8-sig", dtype=str)
    df.columns = df.columns.str.lower()
    salida = pd.DataFrame(
        {
            "anio": anio,
            "mun": df["mun"].str.zfill(3),
            "nom_mun": df["nom_mun"],
            "loc": df["loc"].str.zfill(4),
            "nom_loc": df["nom_loc"],
            "lat": df["latitud"].map(lambda v: _dms_a_decimal(v, negativo=False)),
            "lon": df["longitud"].map(lambda v: _dms_a_decimal(v, negativo=True)),
        }
    )
    for destino, candidatas in _COLUMNAS_ITER.items():
        col = next((c for c in candidatas if c in df.columns), None)
        salida[destino] = _a_numero(df[col]) if col else pd.NA
    return salida


def serie_poblacion() -> pd.DataFrame:
    """Población total del municipio y de la cabecera, por levantamiento, para Magdalena y los orígenes."""
    filas = []
    municipios = {config.CVE_MUN_MAGDALENA: "Magdalena", **config.MUNICIPIOS_ORIGEN}
    for anio in config.URLS_ITER:
        df = leer_iter(anio)
        for mun, nombre in municipios.items():
            sub = df[df["mun"] == mun]
            total = sub.loc[sub["loc"] == "0000", "pobtot"]
            cab = sub.loc[sub["loc"] == config.CVE_LOC_CABECERA]
            filas.append(
                {
                    "anio": anio,
                    "mun": mun,
                    "municipio": nombre,
                    "cabecera": cab["nom_loc"].iloc[0] if len(cab) else None,
                    "pob_municipio": int(total.iloc[0]) if len(total) else None,
                    "pob_cabecera": int(cab["pobtot"].iloc[0]) if len(cab) else None,
                }
            )
    out = pd.DataFrame(filas)
    out["pct_en_cabecera"] = out["pob_cabecera"] / out["pob_municipio"] * 100
    return out


def vivienda_magdalena() -> pd.DataFrame:
    """Viviendas de la cabecera de Magdalena (2010 y 2020, los años que publican estas variables)."""
    filas = []
    for anio in (2010, 2020):
        df = leer_iter(anio)
        cab = df[(df["mun"] == config.CVE_MUN_MAGDALENA) & (df["loc"] == config.CVE_LOC_CABECERA)].iloc[0]
        filas.append(cab[["anio", "pobtot", "vivtot", "viv_habitadas", "viv_deshabitadas", "viv_uso_temporal"]])
    out = pd.DataFrame(filas).reset_index(drop=True).astype(int)
    out["hab_por_vivienda"] = out["pobtot"] / out["viv_habitadas"]
    return out


def leer_proyeccion_coespo() -> pd.DataFrame:
    """Proyección CONAPO/COESPO 2025-2040 del municipio, extraída del PDF oficial."""
    import pdfplumber

    with pdfplumber.open(config.DIR_RAW / "coespo" / "Magdalena.pdf") as pdf:
        texto = pdf.pages[0].extract_text()
    patron = re.compile(r"^(20\d\d) ([\d,]+) ([\d.]+)% ([\d,]+) ([\d,]+) ([\d,]+)$", re.MULTILINE)
    filas = [
        {
            "anio": int(m[1]),
            "pob_estado": int(m[2].replace(",", "")),
            "pct_estatal": float(m[3]),
            "pob_municipio": int(m[4].replace(",", "")),
            "mujeres": int(m[5].replace(",", "")),
            "hombres": int(m[6].replace(",", "")),
        }
        for m in patron.finditer(texto)
    ]
    return pd.DataFrame(filas).sort_values("anio").reset_index(drop=True)


# --- DENUE -------------------------------------------------------------------

# Sectores SCIAN que atienden directamente a un visitante.
SECTORES_VISITANTE = {
    "721": "Hospedaje",
    "722": "Alimentos y bebidas",
    "46": "Comercio al por menor",
    "81212": "Baños, sanitarios y estacionamientos",  # 812120 baños públicos
    "81213": "Baños, sanitarios y estacionamientos",  # 812130 sanitarios públicos y bolerías
    "81291": "Baños, sanitarios y estacionamientos",  # 812910 estacionamientos y pensiones
}

_PERSONAL_PUNTO_MEDIO = {
    "0 a 5 personas": 3,
    "6 a 10 personas": 8,
    "11 a 30 personas": 20.5,
    "31 a 50 personas": 40.5,
    "51 a 100 personas": 75.5,
    "101 a 250 personas": 175.5,
    "251 y más personas": 251,
}


@lru_cache(maxsize=None)
def leer_denue() -> pd.DataFrame:
    ruta = next((config.DIR_RAW / "denue").rglob("denue_inegi_26_*.csv"))
    df = pd.read_csv(ruta, encoding="latin1", dtype=str)
    df["latitud"] = pd.to_numeric(df["latitud"], errors="coerce")
    df["longitud"] = pd.to_numeric(df["longitud"], errors="coerce")
    df["personal_estimado"] = df["per_ocu"].map(_PERSONAL_PUNTO_MEDIO)
    return df


def clasificar_sector(codigo_act: str) -> str:
    for prefijo in sorted(SECTORES_VISITANTE, key=len, reverse=True):
        if str(codigo_act).startswith(prefijo):
            return SECTORES_VISITANTE[prefijo]
    return "Otros"


def denue_por_municipio() -> pd.DataFrame:
    """Establecimientos por sector de atención al visitante, por municipio de Sonora, con población 2020."""
    df = leer_denue().copy()
    df["sector"] = df["codigo_act"].map(clasificar_sector)
    tabla = df.pivot_table(index=["cve_mun", "municipio"], columns="sector", values="id", aggfunc="count", fill_value=0)
    tabla = tabla.reset_index().rename(columns={"cve_mun": "mun"})
    pob = leer_iter(2020)
    pob = pob[pob["loc"] == "0000"][["mun", "pobtot"]]
    tabla = tabla.merge(pob, on="mun", how="left")
    tabla["mun"] = tabla["mun"].str.zfill(3)
    return tabla


# --- Clima -------------------------------------------------------------------


def leer_clima(punto: str = "magdalena") -> pd.DataFrame:
    datos = json.loads((config.DIR_RAW / "clima" / f"open_meteo_{punto}.json").read_text(encoding="utf-8"))
    df = pd.DataFrame(datos["daily"]).rename(
        columns={
            "time": "fecha",
            "temperature_2m_max": "t_max",
            "temperature_2m_min": "t_min",
            "precipitation_sum": "precipitacion_mm",
        }
    )
    df["fecha"] = pd.to_datetime(df["fecha"])
    df["punto"] = punto
    return df


def en_ventana_fiestas(fechas: pd.Series) -> pd.Series:
    mmdd = fechas.dt.strftime("%m-%d")
    return (mmdd >= config.FIESTAS_INICIO_MMDD) & (mmdd <= config.FIESTAS_FIN_MMDD)


# --- Wikipedia ---------------------------------------------------------------


def leer_wikipedia() -> pd.DataFrame:
    filas = []
    for archivo in sorted((config.DIR_RAW / "wikipedia").glob("*.json")):
        for item in json.loads(archivo.read_text(encoding="utf-8"))["items"]:
            filas.append(
                {
                    "proyecto": item["project"],
                    "articulo": item["article"],
                    "fecha": pd.to_datetime(item["timestamp"][:8]),
                    "visitas": item["views"],
                }
            )
    return pd.DataFrame(filas)


# --- Rutas -------------------------------------------------------------------


def leer_rutas() -> tuple[pd.DataFrame, dict]:
    """Resumen de rutas OSRM y las geometrías (lista de [lon, lat]) por clave de municipio."""
    datos = json.loads((config.DIR_RAW / "rutas" / "osrm_rutas.json").read_text(encoding="utf-8"))
    resumen = pd.DataFrame(
        [
            {
                "mun": mun,
                "origen": r["origen"],
                "km_carretera": r["distancia_m"] / 1000,
                "horas_auto": r["duracion_s"] / 3600,
                "origen_lat": r["origen_lat"],
                "origen_lon": r["origen_lon"],
            }
            for mun, r in datos.items()
        ]
    ).sort_values("km_carretera")
    geometrias = {mun: r["geometria"] for mun, r in datos.items()}
    return resumen.reset_index(drop=True), geometrias


# --- Registros manuales ------------------------------------------------------


def leer_registro_prensa() -> pd.DataFrame:
    df = pd.read_csv(config.DIR_MANUAL / "registro_cifras_prensa.csv", parse_dates=["fecha_publicacion"])
    df["anio_evento"] = df["anio_evento"].astype("Int64")
    return df


def leer_distancias_prensa() -> pd.DataFrame:
    return pd.read_csv(config.DIR_MANUAL / "registro_distancias_prensa.csv", parse_dates=["fecha_publicacion"])


def leer_comparativos() -> pd.DataFrame:
    return pd.read_csv(config.DIR_MANUAL / "comparativos_turismo_religioso.csv")


def leer_cronologia() -> pd.DataFrame:
    return pd.read_csv(config.DIR_MANUAL / "cronologia.csv")


def construir_tablas() -> None:
    """Escribe a datos/processed/ las tablas limpias que usan los notebooks."""
    config.DIR_PROCESSED.mkdir(parents=True, exist_ok=True)
    serie_poblacion().to_csv(config.DIR_PROCESSED / "poblacion_censal.csv", index=False)
    vivienda_magdalena().to_csv(config.DIR_PROCESSED / "vivienda_magdalena.csv", index=False)
    leer_proyeccion_coespo().to_csv(config.DIR_PROCESSED / "proyeccion_coespo_magdalena.csv", index=False)
    denue_por_municipio().to_csv(config.DIR_PROCESSED / "denue_sectores_por_municipio.csv", index=False)
    print("Tablas escritas en", config.DIR_PROCESSED.relative_to(config.RAIZ))


if __name__ == "__main__":
    construir_tablas()
