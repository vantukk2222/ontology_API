from flask import Flask
from app.config import Config
from app.routes.courses import courses_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Đăng ký các blueprint
    app.register_blueprint(courses_bp)

    @app.route('/', methods=['GET'])
    def hello():
        return "Hello, World!"
  
    return app