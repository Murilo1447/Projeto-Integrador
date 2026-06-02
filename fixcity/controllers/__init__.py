from .auth_controller import register_auth_routes
from .main_controller import register_main_routes
from .media_controller import register_media_routes


def register_routes(app):
    register_auth_routes(app)
    register_media_routes(app)
    register_main_routes(app)
