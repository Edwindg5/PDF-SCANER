from pathlib import Path
from flask import request, jsonify
from pydantic_ai import BinaryContent
from agent import agent
from utils import convertir_reportes_a_json, exportar_dict_a_excel
import os
import tempfile

def procesar_pdf_controller():
    if "file" not in request.files:
        return jsonify({"error": "No se envió ningún archivo PDF"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "El archivo no tiene nombre"}), 400

    try:
        # Guardar temporalmente el PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            file.save(tmp.name)
            temp_path = Path(tmp.name)

        # Ejecutar el agente
        result = agent.run_sync([
            "extraeme la informacion del pdf",
            BinaryContent(data=temp_path.read_bytes(), media_type="application/pdf")
        ])

        # Convertir resultados a JSON/Dict
        report_dicts = convertir_reportes_a_json(result.output, como_json=False)

        # Exportar a Excel
        excel_filename = f"resultados_{Path(file.filename).stem}.xlsx"
        exportar_dict_a_excel(report_dicts, excel_filename)

        # Eliminar el PDF temporal
        os.remove(temp_path)

        return jsonify({
            "mensaje": "Proceso completado correctamente",
            "archivo_excel": excel_filename,
            "datos_extraidos": report_dicts
        })

    except Exception as e:
        return jsonify({"error": f"Error al procesar el PDF: {str(e)}"}), 500
