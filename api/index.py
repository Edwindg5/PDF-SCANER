# api/index.py
import sys
import os
import traceback

# Agregar el directorio padre al path para importar módulos
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Debug: Lista de archivos disponibles
def listar_archivos():
    archivos_info = {
        'current_dir': current_dir,
        'parent_dir': parent_dir,
        'archivos_parent': os.listdir(parent_dir) if os.path.exists(parent_dir) else 'No existe',
        'sys_path': sys.path[:3]  # Solo los primeros 3 para evitar spam
    }
    return archivos_info

try:
    from flask import Flask, render_template
    
    # Intentar importar paso a paso para ver dónde falla
    import_errors = []
    
    try:
        from routes.pdf_routes import pdf_bp
        pdf_bp_status = "OK"
    except Exception as e:
        pdf_bp = None
        pdf_bp_status = f"Error: {str(e)}"
        import_errors.append(f"pdf_routes: {str(e)}")
    
    try:
        from controllers.pdf_controller import mostrar_vista_principal_controller
        controller_status = "OK"
    except Exception as e:
        mostrar_vista_principal_controller = None
        controller_status = f"Error: {str(e)}"
        import_errors.append(f"pdf_controller: {str(e)}")
    
    # Crear la aplicación Flask
    app = Flask(__name__, 
               template_folder=os.path.join(parent_dir, 'templates'),
               static_folder=os.path.join(parent_dir, 'static'))

    # Registrar el blueprint solo si se importó correctamente
    if pdf_bp:
        app.register_blueprint(pdf_bp, url_prefix="/api")

    # Ruta principal en la raíz
    @app.route("/")
    def index():
        if mostrar_vista_principal_controller:
            try:
                return mostrar_vista_principal_controller()
            except Exception as e:
                return f"Error ejecutando controller: {str(e)}<br>Traceback: {traceback.format_exc()}"
        else:
            return f"Controller no disponible: {controller_status}"

    # Ruta para la página de juegos
    @app.route("/juegos")
    def juegos():
        try:
            return render_template('juegos.html')
        except Exception as e:
            return f"Error renderizando juegos.html: {str(e)}"
        
    # Ruta de prueba para debug
    @app.route("/test")
    def test():
        return "La aplicación Flask está funcionando correctamente!"
    
    # Ruta de debug detallada
    @app.route("/debug")
    def debug():
        debug_info = {
            'archivos': listar_archivos(),
            'pdf_bp_status': pdf_bp_status,
            'controller_status': controller_status,
            'import_errors': import_errors,
            'templates_dir': os.path.join(parent_dir, 'templates'),
            'templates_exists': os.path.exists(os.path.join(parent_dir, 'templates')),
        }
        
        if os.path.exists(os.path.join(parent_dir, 'templates')):
            try:
                debug_info['templates_files'] = os.listdir(os.path.join(parent_dir, 'templates'))
            except:
                debug_info['templates_files'] = 'Error listando templates'
        
        html = "<h2>Debug Info</h2>"
        for key, value in debug_info.items():
            html += f"<p><strong>{key}:</strong> {value}</p>"
        
        return html

except ImportError as e:
    from flask import Flask
    app = Flask(__name__)
    
    @app.route("/")
    def error():
        debug_info = listar_archivos()
        return f"""
        <h2>Error de importación Flask</h2>
        <p><strong>Error:</strong> {str(e)}</p>
        <p><strong>Traceback:</strong></p>
        <pre>{traceback.format_exc()}</pre>
        <p><strong>Debug info:</strong></p>
        <pre>{debug_info}</pre>
        """
    
    @app.route("/debug")
    def debug():
        return listar_archivos()

except Exception as e:
    # Si falla todo, crear una app mínima
    from flask import Flask
    app = Flask(__name__)
    
    @app.route("/")
    def error():
        return f"""
        <h2>Error crítico</h2>
        <p><strong>Error:</strong> {str(e)}</p>
        <p><strong>Traceback:</strong></p>
        <pre>{traceback.format_exc()}</pre>
        <p><strong>Debug info:</strong></p>
        <pre>{listar_archivos()}</pre>
        """

# Para desarrollo local
if __name__ == "__main__":
    app.run(debug=True)