# scanner/api/index.py
import sys
import os

# Agregar el directorio padre al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template
from routes.pdf_routes import pdf_bp
from controllers.pdf_controller import mostrar_vista_principal_controller

# Crear la aplicación Flask
app = Flask(__name__, 
           template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates'),
           static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static'))

# Registrar el blueprint para las rutas API
app.register_blueprint(pdf_bp, url_prefix="/api")  

# Ruta principal en la raíz
@app.route("/")
def index():
    return mostrar_vista_principal_controller()

# Ruta para la página de juegos
@app.route("/juegos")
def juegos():
    return render_template('juegos.html')

# Esta es la función que Vercel ejecutará
def handler(request):
    return app(request.environ, lambda status, headers: None)

# Para desarrollo local
if __name__ == "__main__":
    app.run(debug=True)