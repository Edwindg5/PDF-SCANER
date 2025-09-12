# scanner/app.py
from flask import Flask, render_template
from routes.pdf_routes import pdf_bp
from controllers.pdf_controller import mostrar_vista_principal_controller, limpiar_archivos_antiguos
import threading
import time

app = Flask(__name__, template_folder='templates', static_folder='static')

# Registrar el blueprint para las rutas API
app.register_blueprint(pdf_bp, url_prefix="/api")  

# Ruta principal en la raíz
@app.route("/")
def index():
    return mostrar_vista_principal_controller()

# Función para limpieza periódica en segundo plano
def limpieza_periodica():
    while True:
        try:
            # Dormir durante 12 horas
            time.sleep(10 * 60)
            # Ejecutar limpieza
            limpiar_archivos_antiguos()
        except Exception as e:
            print(f"Error en limpieza periódica: {str(e)}")

# Iniciar hilo de limpieza periódica
if __name__ == "__main__":
    # Iniciar el hilo de limpieza en segundo plano
    limpieza_thread = threading.Thread(target=limpieza_periodica, daemon=True)
    limpieza_thread.start()
    
    app.run(debug=True)