"""CLI commands for maintenance tasks."""

import click

from ipam.backup import (
    create_backup,
    list_backups,
    restore_backup,
    verify_backup,
)


def init_cli(app):
    """Register CLI commands with the Flask app."""

    @app.cli.group()
    def backup():
        """Backup and restore commands."""

    @backup.command("list")
    def list_command():
        """List available backups."""
        backups = list_backups()
        for backup_info in backups:
            click.echo(
                f"{backup_info.name}\t"
                f"{backup_info.size_bytes}\t"
                f"{backup_info.created_at}"
            )

    @backup.command("create")
    def create_command():
        """Create a new backup."""
        result = create_backup()
        click.echo(
            f"Created {result['name']} "
            f"(integrity: {result['integrity_message']})"
        )

    @backup.command("verify")
    @click.argument("name")
    def verify_command(name):
        """Verify a backup file."""
        result = verify_backup(name)
        click.echo(f"{result['name']} integrity: {result['integrity_message']}")

    @backup.command("restore")
    @click.argument("name")
    def restore_command(name):
        """Restore database from a backup."""
        result = restore_backup(name)
        click.echo(
            f"Restored {result['name']} "
            f"(integrity: {result['integrity_message']})"
        )
