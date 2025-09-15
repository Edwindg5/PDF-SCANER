# scanner/routes/pdf_routes.py
from flask import Blueprint
from controllers.pdf_controller_vercel import (  # Cambiar la importación
    procesar_pdf_controller,
    descargar_excel_controller,
    mostrar_resultados_controller,
    descargar_filtrado_controller
)

pdf_bp = Blueprint("pdf", __name__)

# Las rutas siguen igual, pero ahora usan session_id en lugar de nombres de archivo
pdf_bp.add_url_rule("/procesar-pdf", view_func=procesar_pdf_controller, methods=["POST"])
pdf_bp.add_url_rule("/resultados/<session_id>", view_func=mostrar_resultados_controller, methods=["GET"])
pdf_bp.add_url_rule("/descargar-excel/<session_id>", view_func=descargar_excel_controller, methods=["GET"])
pdf_bp.add_url_rule("/descargar-filtrado", view_func=descargar_filtrado_controller, methods=["POST"])