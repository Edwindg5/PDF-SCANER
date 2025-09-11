from flask import Flask
from routes.pdf_routes import pdf_bp  

app = Flask(__name__)

# Registrar el blueprint
app.register_blueprint(pdf_bp, url_prefix="/api")  

if __name__ == "__main__":
    app.run(debug=True)
