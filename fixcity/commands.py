import click
from flask import Flask

from .models.user_model import tornar_usuario_admin


def register_commands(app: Flask) -> None:
    @app.cli.command("tornar-admin")
    @click.argument("email")
    def tornar_admin_command(email: str) -> None:
        """Promove uma conta existente a administradora."""
        email_normalizado = email.strip().lower()
        if not tornar_usuario_admin(email_normalizado):
            raise click.ClickException(
                f"Nenhuma conta encontrada para o e-mail {email_normalizado}."
            )

        click.echo(f"A conta {email_normalizado} agora e administradora.")
