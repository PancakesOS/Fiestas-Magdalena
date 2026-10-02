"""Descarga de todas las fuentes externas del proyecto a datos/raw/.

Cada fuente es reanudable: si el archivo destino ya existe, se omite (usa
--forzar para volver a bajarla). Uso:

    uv run python -m src.descarga                 # todas las fuentes
    uv run python -m src.descarga --solo iter clima
    uv run python -m src.descarga --forzar --solo wikipedia

Fuentes:
    iter       Censos y conteos INEGI 2000, 2005, 2010 y 2020 (resultados por localidad, Sonora)
    denue      Directorio Estadístico Nacional de Unidades Económicas, Sonora (INEGI)
    coespo     Proyección municipal 2025-2040 de Magdalena (COESPO Sonora / CONAPO), PDF
    clima      Temperatura y precipitación diaria 1995-hoy (Open-Meteo, reanálisis ERA5)
    wikipedia  Visitas diarias a artículos de Wikipedia (API de Wikimedia)
    rutas      Distancia y trazo por carretera desde cada origen a Magdalena (OSRM)
    fuentes    Estado HTTP y copia en Internet Archive de cada nota de prensa citada
"""

import argparse
import json
import logging
import time
import zipfile
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

from src import config

log = logging.getLogger("descarga")

SESION = requests.Session()
SESION.headers.update({"User-Agent": config.USER_AGENT})


def _get(url: str, intentos: int = 4, **kwargs) -> requests.Response:
    """GET con reintentos y espera exponencial para errores de red o 5xx/429."""
    for intento in range(1, intentos + 1):
        try:
            resp = SESION.get(url, timeout=kwargs.pop("timeout", 120), **kwargs)
            if resp.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"HTTP {resp.status_code}")
            return resp
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as err:
            if intento == intentos:
                raise
            espera = 2**intento
            log.warning("  %s (intento %d/%d), reintento en %ds", err, intento, intentos, espera)
            time.sleep(espera)
    raise RuntimeError("inalcanzable")


def _descargar_archivo(url: str, destino: Path, forzar: bool) -> Path:
    if destino.exists() and not forzar:
        log.info("  ya existe %s", destino.relative_to(config.RAIZ))
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    resp = _get(url, stream=True)
    resp.raise_for_status()
    tmp = destino.with_suffix(destino.suffix + ".part")
    with tmp.open("wb") as f:
        for bloque in resp.iter_content(chunk_size=1 << 20):
            f.write(bloque)
    tmp.rename(destino)
    log.info("  %s (%.1f MB)", destino.relative_to(config.RAIZ), destino.stat().st_size / 1e6)
    return destino


def _extraer_zip(zip_path: Path, destino: Path) -> None:
    if destino.exists() and any(destino.rglob("*.csv")):
        return
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(destino)


def descargar_iter(forzar: bool) -> None:
    for anio, url in config.URLS_ITER.items():
        log.info("ITER %d", anio)
        zip_path = _descargar_archivo(url, config.DIR_RAW / "inegi" / f"iter_26_{anio}.zip", forzar)
        _extraer_zip(zip_path, config.DIR_RAW / "inegi" / f"iter_26_{anio}")


def descargar_denue(forzar: bool) -> None:
    log.info("DENUE Sonora")
    zip_path = _descargar_archivo(config.URL_DENUE_SONORA, config.DIR_RAW / "denue" / "denue_26.zip", forzar)
    _extraer_zip(zip_path, config.DIR_RAW / "denue" / "denue_26")


def descargar_coespo(forzar: bool) -> None:
    log.info("COESPO proyección Magdalena")
    _descargar_archivo(config.URL_COESPO_MAGDALENA, config.DIR_RAW / "coespo" / "Magdalena.pdf", forzar)


def _coordenadas_cabeceras() -> pd.DataFrame:
    """Lat/lon de las cabeceras (localidad 0001) desde el ITER 2020."""
    from src.procesamiento import leer_iter

    iter20 = leer_iter(2020)
    cab = iter20[(iter20["loc"] == config.CVE_LOC_CABECERA) & (iter20["mun"] != "000")]
    return cab[["mun", "nom_mun", "nom_loc", "lat", "lon"]].reset_index(drop=True)


def descargar_clima(forzar: bool) -> None:
    """Serie diaria completa por punto; el filtro a la ventana de fiestas se hace al procesar."""
    coords = _coordenadas_cabeceras().set_index("mun")
    puntos = {"magdalena": config.CVE_MUN_MAGDALENA, "imuris": "035", "nogales": "043"}
    fin = (date.today() - timedelta(days=7)).isoformat()
    for nombre, mun in puntos.items():
        destino = config.DIR_RAW / "clima" / f"open_meteo_{nombre}.json"
        log.info("Clima %s", nombre)
        if destino.exists() and not forzar:
            log.info("  ya existe %s", destino.relative_to(config.RAIZ))
            continue
        params = {
            "latitude": round(coords.loc[mun, "lat"], 4),
            "longitude": round(coords.loc[mun, "lon"], 4),
            "start_date": "1995-01-01",
            "end_date": fin,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
            "timezone": "America/Hermosillo",
        }
        resp = _get(config.URL_OPEN_METEO, params=params)
        resp.raise_for_status()
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(resp.text, encoding="utf-8")
        log.info("  %s", destino.relative_to(config.RAIZ))


def descargar_wikipedia(forzar: bool) -> None:
    fin = (date.today() - timedelta(days=1)).strftime("%Y%m%d")
    for proyecto, articulo in config.ARTICULOS_WIKIPEDIA:
        destino = config.DIR_RAW / "wikipedia" / f"{proyecto}__{articulo}.json"
        log.info("Wikipedia %s / %s", proyecto, articulo)
        if destino.exists() and not forzar:
            log.info("  ya existe %s", destino.relative_to(config.RAIZ))
            continue
        url = (
            f"{config.URL_WIKIMEDIA_PAGEVIEWS}/{proyecto}/all-access/user/"
            f"{requests.utils.quote(articulo, safe='')}/daily/{config.WIKIPEDIA_INICIO}/{fin}"
        )
        resp = _get(url)
        if resp.status_code == 404:
            log.warning("  sin datos (404), se omite")
            continue
        resp.raise_for_status()
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(resp.text, encoding="utf-8")
        log.info("  %s (%d días)", destino.relative_to(config.RAIZ), len(resp.json()["items"]))
        time.sleep(0.5)


def descargar_rutas(forzar: bool) -> None:
    """Ruta más corta por carretera (perfil de auto de OSRM) de cada cabecera de origen a Magdalena.

    El servidor de demostración de OSRM solo ofrece perfil vehicular: es la distancia
    por carretera, no el trazo peatonal real (que usa acotamientos y veredas).
    """
    destino = config.DIR_RAW / "rutas" / "osrm_rutas.json"
    log.info("Rutas OSRM")
    if destino.exists() and not forzar:
        log.info("  ya existe %s", destino.relative_to(config.RAIZ))
        return
    coords = _coordenadas_cabeceras().set_index("mun")
    meta = coords.loc[config.CVE_MUN_MAGDALENA]
    salida = {}
    for mun, nombre in config.MUNICIPIOS_ORIGEN.items():
        orig = coords.loc[mun]
        url = f"{config.URL_OSRM}/{orig.lon},{orig.lat};{meta.lon},{meta.lat}"
        resp = _get(url, params={"overview": "full", "geometries": "geojson"})
        resp.raise_for_status()
        cuerpo = resp.json()
        ruta = cuerpo["routes"][0]
        salida[mun] = {
            "origen": nombre,
            "origen_lat": orig.lat,
            "origen_lon": orig.lon,
            "distancia_m": ruta["distance"],
            "duracion_s": ruta["duration"],
            "geometria": ruta["geometry"]["coordinates"],
        }
        log.info("  %s: %.1f km", nombre, ruta["distance"] / 1000)
        time.sleep(1.0)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(salida, ensure_ascii=False), encoding="utf-8")


def verificar_fuentes(forzar: bool) -> None:
    """Revisa que cada URL del registro manual de prensa siga viva y si tiene copia archivada."""
    destino = config.DIR_RAW / "fuentes" / "estado_fuentes.csv"
    log.info("Verificación de fuentes de prensa")
    if destino.exists() and not forzar:
        log.info("  ya existe %s", destino.relative_to(config.RAIZ))
        return
    registro = pd.read_csv(config.DIR_MANUAL / "registro_cifras_prensa.csv")
    urls = sorted(set(registro["url"].dropna()))
    filas = []
    for url in urls:
        try:
            resp = SESION.get(url, timeout=30, allow_redirects=True)
            estado = resp.status_code
            redirige_a_portada = resp.url.rstrip("/").count("/") <= 3 and url.rstrip("/").count("/") > 3
        except requests.RequestException as err:
            estado, redirige_a_portada = f"error: {type(err).__name__}", None
        archivo = None
        try:
            wb = SESION.get(config.URL_WAYBACK, params={"url": url}, timeout=30).json()
            snap = wb.get("archived_snapshots", {}).get("closest")
            archivo = snap["url"] if snap and snap.get("available") else None
        except (requests.RequestException, ValueError):
            pass
        filas.append(
            {"url": url, "http": estado, "redirige_a_portada": redirige_a_portada, "copia_wayback": archivo}
        )
        log.info("  %s  %s", estado, url[:90])
        time.sleep(0.5)
    destino.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(filas).to_csv(destino, index=False)


FUENTES = {
    "iter": descargar_iter,
    "denue": descargar_denue,
    "coespo": descargar_coespo,
    "clima": descargar_clima,
    "wikipedia": descargar_wikipedia,
    "rutas": descargar_rutas,
    "fuentes": verificar_fuentes,
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--solo", nargs="+", choices=FUENTES, help="descargar solo estas fuentes")
    parser.add_argument("--forzar", action="store_true", help="volver a descargar aunque ya exista")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    for nombre in args.solo or FUENTES:
        FUENTES[nombre](args.forzar)


if __name__ == "__main__":
    main()
