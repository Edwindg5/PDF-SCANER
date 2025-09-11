from flask import Blueprint
from controllers.pdf_controller import procesar_pdf_controller


pdf_bp = Blueprint("pdf", __name__)


pdf_bp.add_url_rule(
    "/procesar-pdf",
    view_func=procesar_pdf_controller,
    methods=["POST"]
)
