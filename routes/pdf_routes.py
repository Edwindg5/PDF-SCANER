from flask import Blueprint
from controllers.pdf_controller import (
    procesar_pdf_controller,
    descargar_excel_controller,
    mostrar_resultados_controller,
    descargar_filtrado_controller
)

pdf_bp = Blueprint("pdf", __name__)

# Ruta para procesar el PDF
pdf_bp.add_url_rule(
    "/procesar-pdf",
    view_func=procesar_pdf_controller,
    methods=["POST"]
)

# Ruta para la vista de resultados
pdf_bp.add_url_rule(
    "/resultados/<nombre_archivo>",
    view_func=mostrar_resultados_controller,
    methods=["GET"]
)

# Ruta para descargar el Excel generado
pdf_bp.add_url_rule(
    "/descargar-excel/<nombre_archivo>",
    view_func=descargar_excel_controller,
    methods=["GET"]
)

# Ruta para descargar datos filtrados
pdf_bp.add_url_rule(
    "/descargar-filtrado",
    view_func=descargar_filtrado_controller,
    methods=["POST"]
)