import pandas as pd

def exportar_dict_a_excel(datos, nombre_archivo="reportes.xlsx"):
    """
    Exporta un diccionario o lista de diccionarios a un archivo Excel.
    
    Parámetros:
        datos (dict | list): diccionario único o lista de diccionarios con la misma estructura
        nombre_archivo (str): nombre del archivo Excel de salida
    """
    # Si recibe un solo diccionario, lo convertimos en lista
    if isinstance(datos, dict):
        datos = [datos]

    # Crear DataFrame a partir de la lista de diccionarios
    df = pd.DataFrame(datos)

    # Exportar a Excel
    df.to_excel(nombre_archivo, index=False)

    print(f"✅ Archivo Excel creado: {nombre_archivo}")
