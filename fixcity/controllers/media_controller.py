from flask import Response, abort, redirect, url_for

from ..models.user_model import buscar_usuario_por_id
from ..utils import mapping_get


def foto_perfil_usuario(user_id: int):
    user = buscar_usuario_por_id(user_id)
    if not user:
        abort(404)

    blob = mapping_get(user, "foto_perfil_blob")
    mime = (mapping_get(user, "foto_perfil_mime", "") or "application/octet-stream").strip()
    if blob:
        return Response(blob, mimetype=mime)

    legacy_path = (mapping_get(user, "foto_perfil", "") or "").strip().replace("\\", "/")
    if legacy_path:
        return redirect(url_for("static", filename=legacy_path))

    abort(404)


def register_media_routes(app):
    app.add_url_rule("/media/perfis/<int:user_id>/", view_func=foto_perfil_usuario, endpoint="foto_perfil_usuario")
