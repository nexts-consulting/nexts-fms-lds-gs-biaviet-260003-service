from flask import Flask

from app.routes.example import bp as example_bp
from app.routes.health import bp as health_bp
from app.routes.redeem_biaviet import bp as redeem_biaviet_bp


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(health_bp)
    app.register_blueprint(example_bp)
    app.register_blueprint(redeem_biaviet_bp)
