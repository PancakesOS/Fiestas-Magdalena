"""Pipeline completo: descarga → tablas procesadas → ejecución de notebooks.

    uv run python main.py                 # todo
    uv run python main.py --sin-descarga  # usa lo que ya está en datos/raw/
    uv run python main.py --solo 03 08    # ejecuta solo esos notebooks
"""

import argparse
import logging
import time

import nbformat
from nbclient import NotebookClient

from src import config, descarga, procesamiento

DIR_NOTEBOOKS = config.RAIZ / "notebooks"


def ejecutar_notebooks(prefijos: list[str] | None) -> None:
    for ruta in sorted(DIR_NOTEBOOKS.glob("[0-9][0-9]_*.ipynb")):
        if prefijos and ruta.name[:2] not in prefijos:
            continue
        inicio = time.time()
        nb = nbformat.read(ruta, as_version=4)
        NotebookClient(nb, timeout=900, kernel_name="python3", resources={"metadata": {"path": str(DIR_NOTEBOOKS)}}).execute()
        nbformat.write(nb, ruta)
        print(f"  {ruta.name} ({time.time() - inicio:.0f}s)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sin-descarga", action="store_true", help="no intentar descargar fuentes faltantes")
    parser.add_argument("--solo", nargs="+", help="prefijos de notebooks a ejecutar (ej. 01 03)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")

    if not args.sin_descarga:
        print("1/3 Descarga de fuentes")
        for funcion in descarga.FUENTES.values():
            funcion(forzar=False)
    print("2/3 Tablas procesadas")
    procesamiento.construir_tablas()
    print("3/3 Notebooks")
    ejecutar_notebooks(args.solo)


if __name__ == "__main__":
    main()
