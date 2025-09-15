# scanner/controllers/pdf_controller_vercel.py
from pathlib import Path
from flask import request, jsonify, render_template, send_file, make_response
from pydantic_ai import BinaryContent
from agent.multi_account_agent import multi_agent
from utils import convertir_reportes_a_json, exportar_dict_a_excel
import tempfile
import PyPDF2
import openpyxl
import json
import io
import datetime
import time
import re

def obtener_orden_columnas_correcto():
    """
    Retorna el orden correcto de las columnas según la estructura del PDF
    """
    return [
        # DATOS DE SOLICITANTE
        'clave_de_la_muestra', 'folio', 'nombre', 'direccion', 'telefono', 
        'municipio', 'estado', 'colonia', 'correo',
        
        # DATOS Y CONDICIONES DE LA MUESTRA
        'estado_de_procedencia', 'municipio_muestra', 'localidad', 'cantidad', 
        'aceptable', 'fecha_de_muestreo', 'tabla_lote', 'profundidad_de_muestreo',
        'cultivo_anterior', 'cultivo_a_establecer', 'meta_de_rendimiento',
        'incorporo_residuos_de_cosecha', 'nombre_del_productor',
        'coordenadas_latitud', 'coordenadas_longitud',
        
        # PARÁMETROS FÍSICOS DEL SUELO
        'arcilla', 'limo', 'arena', 'textura', 'porcentaje_saturacion', 
        'densidad_aparente_DAP',
        
        # PARÁMETROS QUÍMICOS DEL SUELO
        'ph_agua_suelo', 'ph_agua_suelo_interpretacion', 'ph_cacl2', 
        'ph_cacl2_interpretacion', 'ph_kcl', 'ph_kcl_interpretacion',
        'carbonato_calcio_equivalente', 'carbonato_calcio_interpretacion',
        'conductividad_electrica', 'conductividad_electrica_interpretacion',
        
        # RESULTADOS DE FERTILIDAD DE SUELO
        'materia_organica', 'materia_organica_interpretacion', 'fosforo', 
        'fosforo_interpretacion', 'n_inorganico', 'n_inorganico_interpretacion',
        'potasio', 'potasio_interpretacion', 'calcio', 'calcio_interpretacion',
        'magnesio', 'magnesio_interpretacion', 'sodio', 'sodio_interpretacion',
        'azufre', 'azufre_interpretacion',
        
        # CATIONES INTERCAMBIABLES
        'ca_porcentaje', 'ca_me_100g', 'mg_porcentaje', 'mg_me_100g',
        'k_porcentaje', 'k_me_100g', 'na_porcentaje', 'na_me_100g',
        'al_porcentaje', 'al_me_100g', 'h_porcentaje', 'h_me_100g', 'cic',
        
        # MICRONUTRIENTES
        'hierro', 'hierro_interpretacion', 'cobre', 'cobre_interpretacion',
        'zinc', 'zinc_interpretacion', 'manganeso', 'manganeso_interpretacion',
        'boro', 'boro_interpretacion',
        
        # RELACIONES ENTRE CATIONES
        'ca_mg_relacion', 'ca_mg_interpretacion', 'mg_k_relacion', 
        'mg_k_interpretacion', 'ca_k_relacion', 'ca_k_interpretacion',
        'ca_mg_k_relacion', 'ca_mg_k_interpretacion', 'k_mg_relacion', 
        'k_mg_interpretacion'
    ]

def aplicar_orden_dataframe(data_list):
    """
    Aplica el orden correcto a una lista de diccionarios
    """
    orden_columnas = obtener_orden_columnas_correcto()
    
    if not data_list:
        return data_list
    
    # Obtener todas las columnas únicas
    todas_columnas = set()
    for item in data_list:
        todas_columnas.update(item.keys())
    
    # Solo incluir columnas que existen en los datos
    columnas_existentes = [col for col in orden_columnas if col in todas_columnas]
    columnas_adicionales = [col for col in todas_columnas if col not in orden_columnas]
    orden_final = columnas_existentes + columnas_adicionales
    
    # Reorganizar cada diccionario
    data_ordenada = []
    for item in data_list:
        item_ordenado = {}
        for col in orden_final:
            if col in item:
                item_ordenado[col] = item[col]
        data_ordenada.append(item_ordenado)
    
    return data_ordenada

def generar_nombre_archivo(base, extension):
    """
    Genera un nombre único para un archivo con timestamp
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base_limpio = re.sub(r'[\\/*?:"<>|]', "", base)
    return f"{base_limpio}_{timestamp}.{extension}"

# Cache en memoria para almacenar datos temporalmente
CACHE_DATOS = {}

def mostrar_vista_principal_controller():
    """
    Renderiza la vista principal con el formulario para subir PDFs
    """
    return render_template("index.html")

def procesar_pdf_controller():
    if "file" not in request.files:
        return jsonify({"error": "No se envió ningún archivo PDF"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "El archivo no tiene nombre"}), 400

    temp_path = None
    try:
        # Guardar temporalmente el PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            file.save(tmp.name)
            temp_path = Path(tmp.name)
        
        # Verificar el número de páginas del PDF
        pdf_reader = PyPDF2.PdfReader(str(temp_path))
        num_pages = len(pdf_reader.pages)
        
        # Validar si el PDF tiene más de 60 páginas
        if num_pages > 60:
            return jsonify({
                "error": "El archivo excede el tamaño máximo permitido por la aplicación (60 páginas)",
                "paginas": num_pages
            }), 413
            
        print(f"PDF cargado exitosamente con {num_pages} páginas")
        
        # Leer los bytes del archivo para el procesamiento por el agente
        pdf_bytes = temp_path.read_bytes()
        
        # Usar el multi_agent
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
        
        # Aplicar orden correcto
        report_dicts = aplicar_orden_dataframe(report_dicts)

        # Generar ID único para esta sesión
        session_id = generar_nombre_archivo("session", "")
        
        # Guardar datos en cache en memoria
        CACHE_DATOS[session_id] = {
            'datos': report_dicts,
            'timestamp': time.time(),
            'filename_base': Path(file.filename).stem
        }
        
        # Limpiar cache antiguo (más de 30 minutos)
        limpiar_cache_antiguo()
        
        return jsonify({
            "mensaje": f"Proceso completado correctamente. Se extrajeron {len(report_dicts)} reportes del PDF de {num_pages} páginas.",
            "session_id": session_id,
            "redirect_url": f"/api/resultados/{session_id}",
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
        else:
            return jsonify({
                "error": f"Error al procesar el PDF: {error_msg}",
                "detalle": "Error interno del sistema."
            }), 500
    
    finally:
        # Eliminar archivo temporal
        try:
            if temp_path and temp_path.exists():
                temp_path.unlink()
                print("Archivo temporal eliminado correctamente")
        except Exception as e:
            print(f"Error al eliminar archivo temporal: {str(e)}")

def limpiar_cache_antiguo():
    """
    Elimina entradas del cache más antiguas de 30 minutos
    """
    tiempo_actual = time.time()
    limite_tiempo = 30 * 60  # 30 minutos
    
    keys_a_eliminar = []
    for key, value in CACHE_DATOS.items():
        if tiempo_actual - value['timestamp'] > limite_tiempo:
            keys_a_eliminar.append(key)
    
    for key in keys_a_eliminar:
        del CACHE_DATOS[key]
    
    print(f"Cache limpiado: {len(keys_a_eliminar)} entradas eliminadas")

def mostrar_resultados_controller(session_id):
    """
    Muestra la vista de resultados con la tabla de datos desde el cache
    """
    try:
        # Verificar que existe en el cache
        if session_id not in CACHE_DATOS:
            return jsonify({"error": "La sesión no existe o ha caducado"}), 404
        
        datos_sesion = CACHE_DATOS[session_id]
        datos = datos_sesion['datos']
        
        # Obtener columnas de los datos
        columnas = []
        if datos:
            columnas = list(datos[0].keys())
        
        return render_template(
            "resultados.html", 
            datos=datos, 
            columnas=columnas, 
            session_id=session_id,
            dias_caducidad=30  # minutos
        )
    
    except Exception as e:
        return jsonify({"error": f"Error al mostrar los resultados: {str(e)}"}), 500

def descargar_excel_controller(session_id):
    """
    Genera y descarga el archivo Excel desde el cache
    """
    try:
        # Verificar que existe en el cache
        if session_id not in CACHE_DATOS:
            return jsonify({"error": "La sesión no existe o ha caducado"}), 404
        
        datos_sesion = CACHE_DATOS[session_id]
        datos = datos_sesion['datos']
        filename_base = datos_sesion['filename_base']
        
        # Crear Excel en memoria
        excel_buffer = exportar_dict_a_excel(datos)
        
        # Generar nombre de archivo
        excel_filename = generar_nombre_archivo(filename_base, "xlsx")
        
        # Crear respuesta
        response = make_response(excel_buffer.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = f'attachment; filename="{excel_filename}"'
        
        return response
    
    except Exception as e:
        return jsonify({"error": f"Error al generar el archivo Excel: {str(e)}"}), 500

def descargar_filtrado_controller():
    """
    Genera un archivo Excel con los datos filtrados
    """
    try:
        # Obtener los datos filtrados del JSON enviado por POST
        if not request.is_json:
            return jsonify({"error": "Se esperaba formato JSON"}), 400
            
        datos_filtrados = request.json.get('datos_filtrados')
        if not datos_filtrados:
            return jsonify({"error": "No se recibieron datos filtrados"}), 400
        
        # Aplicar orden correcto a los datos filtrados
        datos_ordenados = aplicar_orden_dataframe(datos_filtrados)
        
        # Crear Excel en memoria
        excel_buffer = exportar_dict_a_excel(datos_ordenados)
        
        # Generar nombre de archivo
        filtrado_filename = generar_nombre_archivo("datos_filtrados", "xlsx")
        
        # Crear respuesta
        response = make_response(excel_buffer.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = f'attachment; filename="{filtrado_filename}"'
        
        return response
        
    except Exception as e:
        return jsonify({"error": f"Error al generar el Excel filtrado: {str(e)}"}), 500