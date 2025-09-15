# scanner/api/index.py
import sys
import os

# Agregar el directorio padre al path para importar módulos
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

try:
    from flask import Flask, render_template
    from routes.pdf_routes import pdf_bp
    from controllers.pdf_controller import mostrar_vista_principal_controller
    
    # Crear la aplicación Flask
    app = Flask(__name__, 
               template_folder=os.path.join(parent_dir, 'templates'),
               static_folder=os.path.join(parent_dir, 'static'))

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
        
    # Ruta de prueba para debug
    @app.route("/test")
    def test():
        return "La aplicación está funcionando correctamente!"

except ImportError as e:
    from flask import Flask
    app = Flask(__name__)
    
    @app.route("/")
    def error():
        return f"Error de importación: {str(e)}<br>Directorio actual: {current_dir}<br>Directorio padre: {parent_dir}"

# Para desarrollo local
if __name__ == "__main__":
    app.run(debug=True)