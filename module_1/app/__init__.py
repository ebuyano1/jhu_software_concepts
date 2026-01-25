# Application factory creates and configures the Flask app.
# Registers the pages blueprint that contains routes for Home/Projects/Contact.

from flask import Flask

def create_app():
    app = Flask(__name__)
    from app.pages.routes import main_pages_blueprint
    app.register_blueprint(main_pages_blueprint)
    return app
