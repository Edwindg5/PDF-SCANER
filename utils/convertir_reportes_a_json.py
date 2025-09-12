#scanner/ utils/convertir_reportes_a_json.py
import json

def convertir_reportes_a_json(reportes, como_json=True):
    """
    Convierte una lista de objetos ReporteAnalisisSuelo a diccionarios o JSON.

    Parámetros:
        reportes (list): lista de objetos ReporteAnalisisSuelo
        como_json (bool): True para devolver JSON (string), False para lista de dicts

    Retorna:
        str | list: JSON string si como_json=True, lista de diccionarios si False
    """
    lista_dicts = [reporte.__dict__ for reporte in reportes]

    if como_json:
        return json.dumps(lista_dicts, indent=4, ensure_ascii=False)
    return lista_dicts