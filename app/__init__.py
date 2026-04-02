from typing import Optional, Type

from flask import Flask

from app.config import Config
from app.extensions import init_supabase
from app.routes import register_blueprints


def create_app(config_class: Optional[Type[Config]] = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class or Config)

    init_supabase(app)
    register_blueprints(app)

    return app
