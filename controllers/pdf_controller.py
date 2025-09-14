# scanner/controllers/pdf_controller.py
from pathlib import Path
from flask import request, jsonify, render_template, send_file, redirect, url_for, make_response
from pydantic_ai import BinaryContent
from agent.multi_account_agent import multi_agent  # Cambiar esta línea
from utils import convertir_reportes_a_json, exportar_dict_a_excel
import os
import tempfile
import PyPDF2
import pandas as pd
import json
import io
import datetime
import time
import threading
import re


def obtener_orden_columnas_correcto():
    """
    Retorna el orden correcto de las columnas según la estructura del PDF
    """
    return [
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

def aplicar_orden_dataframe(df):
    """
    Aplica el orden correcto a un DataFrame
    """
    orden_columnas = obtener_orden_columnas_correcto()
    
    # Solo incluir columnas que existen en el DataFrame
    columnas_existentes = [col for col in orden_columnas if col in df.columns]
    
    # Añadir cualquier columna adicional que no esté en el orden especificado
    columnas_adicionales = [col for col in df.columns if col not in orden_columnas]
    
    # Combinar en el orden final
    orden_final = columnas_existentes + columnas_adicionales
    
    # Reordenar el DataFrame
    return df[orden_final]

# Directorio donde se guardan los archivos generados
ARCHIVOS_DIR = os.path.join(os.getcwd(), "archivos_generados")
# Tiempo de caducidad en segundos (20 minutos)
TIEMPO_CADUCIDAD = 20 * 60

def crear_directorio_archivos():
    """
    Crea el directorio de archivos si no existe
    """
    try:
        if not os.path.exists(ARCHIVOS_DIR):
            os.makedirs(ARCHIVOS_DIR, exist_ok=True)
            print(f"Directorio creado: {ARCHIVOS_DIR}")
        return True
    except Exception as e:
        print(f"Error al crear directorio {ARCHIVOS_DIR}: {str(e)}")
        return False

# Crear el directorio si no existe al cargar el módulo
crear_directorio_archivos()

def mostrar_vista_principal_controller():
    """
    Renderiza la vista principal con el formulario para subir PDFs
    """
    return render_template("index.html")

def limpiar_archivos_antiguos():
    """
    Elimina archivos generados que no se han utilizado en el tiempo de caducidad (20 minutos)
    y elimina la carpeta si está vacía
    """
    if not os.path.exists(ARCHIVOS_DIR):
        return 0
    
    tiempo_actual = time.time()
    contador_eliminados = 0
    
    # Buscar todos los archivos en el directorio
    for archivo in os.listdir(ARCHIVOS_DIR):
        ruta_archivo = os.path.join(ARCHIVOS_DIR, archivo)
        
        # Verificar si es un archivo (no un directorio)
        if os.path.isfile(ruta_archivo):
            # Obtener el tiempo de última modificación
            tiempo_modificacion = os.path.getmtime(ruta_archivo)
            
            # Si el archivo es más antiguo que 20 minutos, eliminarlo
            if tiempo_actual - tiempo_modificacion > TIEMPO_CADUCIDAD:
                try:
                    os.remove(ruta_archivo)
                    contador_eliminados += 1
                except Exception as e:
                    print(f"Error al eliminar {ruta_archivo}: {str(e)}")
    
    # Intentar eliminar la carpeta si está vacía
    try:
        if os.path.exists(ARCHIVOS_DIR) and not os.listdir(ARCHIVOS_DIR):
            os.rmdir(ARCHIVOS_DIR)
            print("Carpeta archivos_generados eliminada (estaba vacía)")
    except Exception as e:
        print(f"Error al eliminar carpeta: {str(e)}")
    
    print(f"Limpieza automática completada: {contador_eliminados} archivos eliminados")
    return contador_eliminados

def verificar_espacio_disponible():
    """
    Verifica si hay suficiente espacio disponible en el directorio de archivos
    Si el directorio supera 1GB, elimina los archivos más antiguos
    """
    # Crear el directorio si no existe
    if not crear_directorio_archivos():
        return False
        
    limite_tamano = 1 * 1024 * 1024 * 1024  # 1GB en bytes
    
    try:
        tamano_total = sum(os.path.getsize(os.path.join(ARCHIVOS_DIR, f)) for f in os.listdir(ARCHIVOS_DIR) 
                           if os.path.isfile(os.path.join(ARCHIVOS_DIR, f)))
        
        if tamano_total > limite_tamano:
            print(f"Directorio excede el límite de tamaño ({tamano_total} bytes). Limpiando archivos más antiguos...")
            
            # Obtener lista de archivos ordenados por tiempo de modificación (más antiguos primero)
            archivos = [(f, os.path.getmtime(os.path.join(ARCHIVOS_DIR, f))) 
                       for f in os.listdir(ARCHIVOS_DIR) 
                       if os.path.isfile(os.path.join(ARCHIVOS_DIR, f))]
            archivos.sort(key=lambda x: x[1])
            
            # Eliminar archivos hasta que el tamaño sea menor que el 80% del límite
            for archivo, _ in archivos:
                ruta_archivo = os.path.join(ARCHIVOS_DIR, archivo)
                try:
                    tamano_archivo = os.path.getsize(ruta_archivo)
                    os.remove(ruta_archivo)
                    tamano_total -= tamano_archivo
                    if tamano_total < limite_tamano * 0.8:
                        break
                except Exception as e:
                    print(f"Error al eliminar {ruta_archivo}: {str(e)}")
    except Exception as e:
        print(f"Error al verificar espacio disponible: {str(e)}")
    
    return True

def obtener_ruta_archivo(nombre_archivo):
    """
    Obtiene la ruta completa de un archivo y actualiza su fecha de último acceso
    """
    ruta_completa = os.path.join(ARCHIVOS_DIR, nombre_archivo)
    
    # Actualizar la fecha de último acceso si el archivo existe
    if os.path.exists(ruta_completa):
        # Actualizar la fecha de modificación para indicar que se ha accedido al archivo
        os.utime(ruta_completa, None)
    
    return ruta_completa

def generar_nombre_archivo(base, extension):
    """
    Genera un nombre único para un archivo con timestamp
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    # Limpiar caracteres no permitidos en nombres de archivo
    base_limpio = re.sub(r'[\\/*?:"<>|]', "", base)
    return f"{base_limpio}_{timestamp}.{extension}"

def procesar_pdf_controller():
    if "file" not in request.files:
        return jsonify({"error": "No se envió ningún archivo PDF"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "El archivo no tiene nombre"}), 400

    temp_path = None
    try:
        # Verificar espacio disponible y limpiar si es necesario
        if not verificar_espacio_disponible():
            return jsonify({"error": "No se pudo preparar el directorio de archivos"}), 500
        
        # Limpiar archivos antiguos automáticamente
        limpiar_archivos_antiguos()
        
        # Asegurar que el directorio existe después de la limpieza
        if not crear_directorio_archivos():
            return jsonify({"error": "No se pudo crear el directorio de archivos"}), 500
        
        # Guardar temporalmente el PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            file.save(tmp.name)
            temp_path = Path(tmp.name)
        
        # Verificar el número de páginas del PDF
        pdf_reader = None
        try:
            pdf_reader = PyPDF2.PdfReader(str(temp_path))
            num_pages = len(pdf_reader.pages)
            
            # Validar si el PDF tiene más de 60 páginas
            if num_pages > 60:
                return jsonify({
                    "error": "El archivo excede el tamaño máximo permitido por la aplicación (60 páginas)",
                    "paginas": num_pages
                }), 413
                
            print(f"PDF cargado exitosamente con {num_pages} páginas")
        except Exception as e:
            return jsonify({"error": f"Error al leer el PDF: {str(e)}"}), 400
        finally:
            # Asegurarnos de que se libere la referencia al lector PDF
            pdf_reader = None
        
        # Leer los bytes del archivo para el procesamiento por el agente
        pdf_bytes = temp_path.read_bytes()
        
        # Usar el multi_agent en lugar del agent simple
        print("Iniciando procesamiento con multi-agent...")
        result = multi_agent.run_sync([
            f"Extrae toda la información de análisis de suelo de este PDF de {num_pages} páginas. Procesa cada hoja por separado y extrae todos los reportes encontrados.",
            BinaryContent(data=pdf_bytes, media_type="application/pdf")
        ])

        print(f"Procesamiento completado. Reportes extraídos: {len(result.output) if result.output else 0}")

        # Verificar que se obtuvieron resultados
        if not result.output:
            return jsonify({
                "error": "No se pudieron extraer datos del PDF. El documento podría no contener información de análisis de suelo en el formato esperado."
            }), 422

        # Convertir resultados a JSON/Dict
        report_dicts = convertir_reportes_a_json(result.output, como_json=False)

        # Generar nombres de archivo únicos
        nombre_base = Path(file.filename).stem
        excel_filename = generar_nombre_archivo(nombre_base, "xlsx")
        json_filename = generar_nombre_archivo(nombre_base, "json")
        
        # Asegurar que el directorio existe antes de guardar archivos
        if not crear_directorio_archivos():
            return jsonify({"error": "No se pudo crear el directorio de archivos para guardar los resultados"}), 500
        
        # Crear Excel y guardarlo en el directorio de archivos
        try:
            df = pd.DataFrame(report_dicts)
            df = aplicar_orden_dataframe(df)
            ruta_excel = os.path.join(ARCHIVOS_DIR, excel_filename)
            df.to_excel(ruta_excel, index=False)
            print(f"Archivo Excel guardado con orden correcto: {ruta_excel}")
        except Exception as e:
            return jsonify({"error": f"Error al crear archivo Excel: {str(e)}"}), 500
        
        # Guardar también los datos en JSON
        try:
            ruta_json = os.path.join(ARCHIVOS_DIR, json_filename)
            with open(ruta_json, 'w', encoding='utf-8') as f:
                json.dump(report_dicts, f, ensure_ascii=False, indent=4)
            print(f"Archivo JSON guardado: {ruta_json}")
        except Exception as e:
            print(f"Advertencia: No se pudo guardar el archivo JSON: {str(e)}")
            # No es crítico, continuar sin JSON
            
        programar_eliminacion_archivo(ruta_excel)
        if os.path.exists(os.path.join(ARCHIVOS_DIR, json_filename)):
            programar_eliminacion_archivo(os.path.join(ARCHIVOS_DIR, json_filename))
        
        return jsonify({
            "mensaje": f"Proceso completado correctamente. Se extrajeron {len(report_dicts)} reportes del PDF de {num_pages} páginas.",
            "archivo_excel": excel_filename,
            "archivo_json": json_filename,
            "redirect_url": f"/api/resultados/{excel_filename}",
            "reportes_extraidos": len(report_dicts),
            "paginas_procesadas": num_pages
        })

    except Exception as e:
        error_msg = str(e)
        print(f"Error completo al procesar PDF: {error_msg}")
        
        # Mensajes de error más específicos
        if "Content field missing" in error_msg:
            return jsonify({
                "error": "El documento es demasiado complejo para procesar. Intenta con un PDF más pequeño o divide el documento en secciones.",
                "detalle": "El modelo de IA no pudo generar una respuesta válida para este documento."
            }), 422
        elif "quota exceeded" in error_msg.lower() or "rate limit" in error_msg.lower():
            return jsonify({
                "error": "Se han agotado temporalmente los recursos de procesamiento. Inténtalo de nuevo en unos minutos.",
                "detalle": "Límite de API alcanzado."
            }), 429
        elif "token limit" in error_msg.lower():
            return jsonify({
                "error": "El documento es demasiado grande para procesar de una vez. Intenta dividirlo en partes más pequeñas.",
                "detalle": "Límite de tokens excedido."
            }), 413
        else:
            return jsonify({
                "error": f"Error al procesar el PDF: {error_msg}",
                "detalle": "Error interno del sistema."
            }), 500
    
    finally:
        # Intentar eliminar el archivo temporal en el bloque finally
        try:
            if temp_path and os.path.exists(temp_path):
                # Asegurarnos de que no hay referencias abiertas al archivo
                import gc
                gc.collect()  # Forzar la recolección de basura
                os.remove(temp_path)
                print("Archivo temporal eliminado correctamente")
        except Exception as e:
            print(f"Error al eliminar archivo temporal: {str(e)}")

def mostrar_resultados_controller(nombre_archivo):
    """
    Muestra la vista de resultados con la tabla de datos
    """
    try:
        # Verificar que es un archivo Excel
        if not nombre_archivo.endswith('.xlsx'):
            return jsonify({"error": "Formato de archivo no válido"}), 400
        
        # Construir la ruta del archivo
        ruta_excel = obtener_ruta_archivo(nombre_archivo)
        
        # Verificar que el archivo existe
        if not os.path.exists(ruta_excel):
            return jsonify({"error": "El archivo no existe o ha caducado"}), 404
        
        # Cargar los datos del Excel
        df = pd.read_excel(ruta_excel)
        df = aplicar_orden_dataframe(df)
        
        # Obtener los nombres de las columnas
        columnas = df.columns.tolist()
        
        # Convertir los datos a formato JSON para enviar a la vista
        datos = df.to_dict(orient='records')
        
        # Ruta al archivo JSON correspondiente (si existe)
        json_filename = nombre_archivo.replace('.xlsx', '.json')
        
        return render_template(
            "resultados.html", 
            datos=datos, 
            columnas=columnas, 
            nombre_archivo=nombre_archivo,
            json_filename=json_filename,
            # Añadir información sobre la caducidad de archivos
            dias_caducidad=TIEMPO_CADUCIDAD // 60
        )
    
    except Exception as e:
        return jsonify({"error": f"Error al mostrar los resultados: {str(e)}"}), 500

def descargar_excel_controller(nombre_archivo):
    """
    Descarga el archivo Excel generado
    """
    try:
        # Asegurarse de que solo se puedan descargar archivos Excel
        if not nombre_archivo.endswith('.xlsx'):
            return jsonify({"error": "Formato de archivo no válido"}), 400
        
        # Construir la ruta del archivo
        ruta_archivo = obtener_ruta_archivo(nombre_archivo)
        
        # Verificar que el archivo existe
        if not os.path.exists(ruta_archivo):
            return jsonify({"error": "El archivo no existe o ha caducado"}), 404
        
        # Descargar el archivo
        return send_file(
            ruta_archivo,
            as_attachment=True,
            download_name=nombre_archivo
        )
    
    except Exception as e:
        return jsonify({"error": f"Error al descargar el archivo: {str(e)}"}), 500

def descargar_filtrado_controller():
    """
    Genera un archivo Excel con los datos filtrados y lo devuelve para descarga
    """
    try:
        # Verificar espacio disponible y limpiar si es necesario
        if not verificar_espacio_disponible():
            return jsonify({"error": "No se pudo preparar el directorio de archivos"}), 500
        
        # Obtener los datos filtrados del JSON enviado por POST
        if not request.is_json:
            return jsonify({"error": "Se esperaba formato JSON"}), 400
            
        datos_filtrados = request.json.get('datos_filtrados')
        if not datos_filtrados:
            return jsonify({"error": "No se recibieron datos filtrados"}), 400
        
        # Crear un DataFrame a partir de los datos filtrados
        df = pd.DataFrame(datos_filtrados)
        df = aplicar_orden_dataframe(df)
        
        # Generar un nombre de archivo único para el resultado filtrado
        filtrado_filename = generar_nombre_archivo("datos_filtrados", "xlsx")
        ruta_filtrado = os.path.join(ARCHIVOS_DIR, filtrado_filename)
        
        # Guardar en Excel
        df.to_excel(ruta_filtrado, index=False)
        
        # Devolver el archivo para descarga
        return send_file(
            ruta_filtrado,
            as_attachment=True,
            download_name=filtrado_filename
        )
        
    except Exception as e:
        return jsonify({"error": f"Error al generar el Excel filtrado: {str(e)}"}), 500
    
def programar_eliminacion_archivo(ruta_archivo, delay=1200):  # 1200 segundos = 20 minutos
    """
    Programa la eliminación de un archivo específico después del delay especificado
    """
    def eliminar_archivo():
        time.sleep(delay)
        try:
            if os.path.exists(ruta_archivo):
                os.remove(ruta_archivo)
                print(f"Archivo eliminado automáticamente: {ruta_archivo}")
                
                # Verificar si la carpeta está vacía y eliminarla
                if os.path.exists(ARCHIVOS_DIR) and not os.listdir(ARCHIVOS_DIR):
                    os.rmdir(ARCHIVOS_DIR)
                    print("Carpeta archivos_generados eliminada (estaba vacía)")
        except Exception as e:
            print(f"Error al eliminar archivo programado {ruta_archivo}: {str(e)}")
    
    # Ejecutar en un hilo separado
    thread = threading.Thread(target=eliminar_archivo, daemon=True)
    thread.start()