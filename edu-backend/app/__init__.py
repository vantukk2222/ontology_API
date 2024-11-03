from flask import Flask
from app.config import Config
from app.routes.courses import courses_bp
from app.routes.structure import structure_bp
from app.routes.search import search_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Register blueprints
    app.register_blueprint(courses_bp)
    app.register_blueprint(structure_bp)
    app.register_blueprint(search_bp)

    @app.route('/', methods=['GET'])
    def hello():
        return "Hello, World!"
  
    return app
