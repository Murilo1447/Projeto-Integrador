import click
from flask import Flask

from .models.user_model import tornar_usuario_admin, tornar_usuario_superuser


def _normalizar_email(email: str) -> str:
    return email.strip().lower()


def register_commands(app: Flask) -> None:
    @app.cli.command("tornar-admin")
    @click.argument("email")
    def tornar_admin_command(email: str) -> None:
        """Promove uma conta existente a administradora."""
        email_normalizado = _normalizar_email(email)
        if not tornar_usuario_admin(email_normalizado):
            raise click.ClickException(
                f"Nenhuma conta encontrada para o e-mail {email_normalizado}."
            )

        click.echo(f"A conta {email_normalizado} agora e administradora.")

    @app.cli.command("tornar-superuser")
    @click.argument("email")
    def tornar_superuser_command(email: str) -> None:
        """Promove uma conta existente ao nivel maximo de acesso."""
        email_normalizado = _normalizar_email(email)
        if not tornar_usuario_superuser(email_normalizado):
            raise click.ClickException(
                f"Nenhuma conta encontrada para o e-mail {email_normalizado}."
            )

        click.echo(f"A conta {email_normalizado} agora e superuser.")
