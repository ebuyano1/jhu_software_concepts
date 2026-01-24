from flask import Flask

def create_app():
    app = Flask(__name__)
    from app.pages.routes import main_pages_blueprint
    app.register_blueprint(main_pages_blueprint)
    return app
