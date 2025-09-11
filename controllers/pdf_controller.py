from pathlib import Path
from flask import request, jsonify, render_template, send_file, redirect, url_for, make_response
from pydantic_ai import BinaryContent
from agent import agent
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

# Directorio donde se guardan los archivos generados
ARCHIVOS_DIR = os.path.join(os.getcwd(), "archivos_generados")
# Tiempo de caducidad en segundos (3 días)
TIEMPO_CADUCIDAD = 3 * 24 * 60 * 60  

# Crear el directorio si no existe
os.makedirs(ARCHIVOS_DIR, exist_ok=True)

def mostrar_vista_principal_controller():
    """
    Renderiza la vista principal con el formulario para subir PDFs
    """
    return render_template("index.html")

def limpiar_archivos_antiguos():
    """
    Elimina archivos generados que no se han utilizado en el tiempo de caducidad
    """
    tiempo_actual = time.time()
    contador_eliminados = 0
    
    # Buscar todos los archivos en el directorio
    for archivo in os.listdir(ARCHIVOS_DIR):
        ruta_archivo = os.path.join(ARCHIVOS_DIR, archivo)
        
        # Verificar si es un archivo (no un directorio)
        if os.path.isfile(ruta_archivo):
            # Obtener el tiempo de última modificación
            tiempo_modificacion = os.path.getmtime(ruta_archivo)
            
            # Si el archivo es más antiguo que el tiempo de caducidad, eliminarlo
            if tiempo_actual - tiempo_modificacion > TIEMPO_CADUCIDAD:
                try:
                    os.remove(ruta_archivo)
                    contador_eliminados += 1
                except Exception as e:
                    print(f"Error al eliminar {ruta_archivo}: {str(e)}")
    
    print(f"Limpieza automática completada: {contador_eliminados} archivos eliminados")
    return contador_eliminados

def verificar_espacio_disponible():
    """
    Verifica si hay suficiente espacio disponible en el directorio de archivos
    Si el directorio supera 1GB, elimina los archivos más antiguos
    """
    limite_tamano = 1 * 1024 * 1024 * 1024  # 1GB en bytes
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
                os.remove(ruta_archivo)
                tamano_total -= os.path.getsize(ruta_archivo)
                if tamano_total < limite_tamano * 0.8:
                    break
            except Exception as e:
                print(f"Error al eliminar {ruta_archivo}: {str(e)}")

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
        verificar_espacio_disponible()
        
        # Limpiar archivos antiguos automáticamente
        limpiar_archivos_antiguos()
        
        # Guardar temporalmente el PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            file.save(tmp.name)
            temp_path = Path(tmp.name)
        
        # Verificar el número de páginas del PDF
        pdf_reader = None
        try:
            pdf_reader = PyPDF2.PdfReader(str(temp_path))
            num_pages = len(pdf_reader.pages)
            
            # Validar si el PDF tiene más de 30 páginas
            if num_pages > 30:
                return jsonify({
                    "error": "El archivo excede el tamaño máximo permitido por la aplicación (30 páginas)",
                    "paginas": num_pages
                }), 413
        except Exception as e:
            return jsonify({"error": f"Error al leer el PDF: {str(e)}"}), 400
        finally:
            # Asegurarnos de que se libere la referencia al lector PDF
            pdf_reader = None
        
        # Leer los bytes del archivo para el procesamiento por el agente
        pdf_bytes = temp_path.read_bytes()
        
        # Ejecutar el agente
        result = agent.run_sync([
            "extraeme la informacion del pdf",
            BinaryContent(data=pdf_bytes, media_type="application/pdf")
        ])

        # Convertir resultados a JSON/Dict
        report_dicts = convertir_reportes_a_json(result.output, como_json=False)

        # Generar nombres de archivo únicos
        nombre_base = Path(file.filename).stem
        excel_filename = generar_nombre_archivo(nombre_base, "xlsx")
        json_filename = generar_nombre_archivo(nombre_base, "json")
        
        # Crear Excel y guardarlo en el directorio de archivos
        df = pd.DataFrame(report_dicts)
        ruta_excel = os.path.join(ARCHIVOS_DIR, excel_filename)
        df.to_excel(ruta_excel, index=False)
        
        # Guardar también los datos en JSON
        ruta_json = os.path.join(ARCHIVOS_DIR, json_filename)
        with open(ruta_json, 'w', encoding='utf-8') as f:
            json.dump(report_dicts, f, ensure_ascii=False, indent=4)

        return jsonify({
            "mensaje": "Proceso completado correctamente",
            "archivo_excel": excel_filename,
            "archivo_json": json_filename,
            "redirect_url": f"/api/resultados/{excel_filename}"
        })

    except Exception as e:
        return jsonify({"error": f"Error al procesar el PDF: {str(e)}"}), 500
    
    finally:
        # Intentar eliminar el archivo temporal en el bloque finally
        try:
            if temp_path and os.path.exists(temp_path):
                # Asegurarnos de que no hay referencias abiertas al archivo
                import gc
                gc.collect()  # Forzar la recolección de basura
                os.remove(temp_path)
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
            return jsonify({"error": "El archivo no existe"}), 404
        
        # Cargar los datos del Excel
        df = pd.read_excel(ruta_excel)
        
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
            dias_caducidad=TIEMPO_CADUCIDAD // (24 * 60 * 60)
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
            return jsonify({"error": "El archivo no existe"}), 404
        
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
        verificar_espacio_disponible()
        
        # Obtener los datos filtrados del JSON enviado por POST
        if not request.is_json:
            return jsonify({"error": "Se esperaba formato JSON"}), 400
            
        datos_filtrados = request.json.get('datos_filtrados')
        if not datos_filtrados:
            return jsonify({"error": "No se recibieron datos filtrados"}), 400
        
        # Crear un DataFrame a partir de los datos filtrados
        df = pd.DataFrame(datos_filtrados)
        
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