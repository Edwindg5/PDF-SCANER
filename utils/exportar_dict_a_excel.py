# scanner/utils/exportar_dict_a_excel.py
import pandas as pd

def exportar_dict_a_excel(datos, nombre_archivo="reportes.xlsx", aplicar_orden=True):
    """
    Exporta un diccionario o lista de diccionarios a un archivo Excel.
    
    Parámetros:
        datos (dict | list): diccionario único o lista de diccionarios con la misma estructura
        nombre_archivo (str): nombre del archivo Excel de salida
        aplicar_orden (bool): si aplicar el orden específico de columnas
    """
    # Si recibe un solo diccionario, lo convertimos en lista
    if isinstance(datos, dict):
        datos = [datos]

    # Crear DataFrame a partir de la lista de diccionarios
    df = pd.DataFrame(datos)
    
    if aplicar_orden:
        # Orden específico de columnas según la imagen del PDF
        orden_columnas = [
            # DATOS DE SOLICITANTE
            'clave_de_la_muestra',
            'folio',
            'nombre',
            'direccion',
            'telefono',
            'municipio',
            'estado',
            'colonia',
            'correo',
            
            # DATOS Y CONDICIONES DE LA MUESTRA
            'estado_de_procedencia',
            'municipio_muestra',
            'localidad',
            'cantidad',
            'aceptable',
            'fecha_de_muestreo',
            'tabla_lote',
            'profundidad_de_muestreo',
            'cultivo_anterior',
            'cultivo_a_establecer',
            'meta_de_rendimiento',
            'incorporo_residuos_de_cosecha',
            'nombre_del_productor',
            'coordenadas_latitud',
            'coordenadas_longitud',
            
            # PARÁMETROS FÍSICOS DEL SUELO
            'arcilla',
            'limo',
            'arena',
            'textura',
            'porcentaje_saturacion',
            'densidad_aparente_DAP',
            
            # PARÁMETROS QUÍMICOS DEL SUELO
            'ph_agua_suelo',
            'ph_agua_suelo_interpretacion',
            'ph_cacl2',
            'ph_cacl2_interpretacion',
            'ph_kcl',
            'ph_kcl_interpretacion',
            'carbonato_calcio_equivalente',
            'carbonato_calcio_interpretacion',
            'conductividad_electrica',
            'conductividad_electrica_interpretacion',
            
            # RESULTADOS DE FERTILIDAD DE SUELO
            'materia_organica',
            'materia_organica_interpretacion',
            'fosforo',
            'fosforo_interpretacion',
            'n_inorganico',
            'n_inorganico_interpretacion',
            'potasio',
            'potasio_interpretacion',
            'calcio',
            'calcio_interpretacion',
            'magnesio',
            'magnesio_interpretacion',
            'sodio',
            'sodio_interpretacion',
            'azufre',
            'azufre_interpretacion',
            
            # CATIONES INTERCAMBIABLES % DE SATURACIÓN
            'ca_porcentaje',
            'ca_me_100g',
            'mg_porcentaje',
            'mg_me_100g',
            'k_porcentaje',
            'k_me_100g',
            'na_porcentaje',
            'na_me_100g',
            'al_porcentaje',
            'al_me_100g',
            'h_porcentaje',
            'h_me_100g',
            'cic',
            
            # MICRONUTRIENTES
            'hierro',
            'hierro_interpretacion',
            'cobre',
            'cobre_interpretacion',
            'zinc',
            'zinc_interpretacion',
            'manganeso',
            'manganeso_interpretacion',
            'boro',
            'boro_interpretacion',
            
            # RELACIONES ENTRE CATIONES
            'ca_mg_relacion',
            'ca_mg_interpretacion',
            'mg_k_relacion',
            'mg_k_interpretacion',
            'ca_k_relacion',
            'ca_k_interpretacion',
            'ca_mg_k_relacion',
            'ca_mg_k_interpretacion',
            'k_mg_relacion',
            'k_mg_interpretacion'
        ]
        
        # Reordenar columnas según el orden especificado
        # Solo incluir columnas que existen en el DataFrame
        columnas_existentes = [col for col in orden_columnas if col in df.columns]
        
        # Añadir cualquier columna adicional que no esté en el orden especificado
        columnas_adicionales = [col for col in df.columns if col not in orden_columnas]
        
        # Combinar en el orden final
        orden_final = columnas_existentes + columnas_adicionales
        
        # Reordenar el DataFrame
        df = df[orden_final]

    # Exportar a Excel
    df.to_excel(nombre_archivo, index=False)

    print(f"✅ Archivo Excel creado: {nombre_archivo}")
    
    return df