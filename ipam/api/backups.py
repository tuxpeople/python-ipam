"""Backup and restore API endpoints."""

from flask_restx import Namespace, Resource, fields

from flask import request

from ipam.api.models import backup_model, error_model, pagination_model
from ipam.backup import (
    create_backup,
    list_backups,
    restore_backup,
    verify_backup,
)

api = Namespace("backups", description="Backup and restore operations")

backup = api.model("Backup", backup_model)
error = api.model("Error", error_model)
pagination = api.model("Pagination", pagination_model)

backup_list = api.model(
    "BackupList",
    {
        "data": fields.List(fields.Nested(backup)),
        "pagination": fields.Nested(pagination),
    },
)


@api.route("")
class BackupList(Resource):
    @api.doc("list_backups")
    @api.marshal_with(backup_list)
    @api.param("page", "Page number", type=int, default=1)
    @api.param("per_page", "Items per page", type=int, default=50)
    def get(self):
        """List all backups."""
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 50, type=int)
        backups = list_backups()
        total = len(backups)
        start = (page - 1) * per_page
        end = start + per_page

        return {
            "data": [
                {
                    "name": b.name,
                    "size_bytes": b.size_bytes,
                    "created_at": b.created_at,
                }
                for b in backups[start:end]
            ],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_items": total,
                "total_pages": (total + per_page - 1) // per_page,
            },
        }

    @api.doc("create_backup")
    @api.marshal_with(backup, code=201)
    @api.response(400, "Validation Error", error)
    def post(self):
        """Create a new backup."""
        try:
            result = create_backup()
        except ValueError as e:
            api.abort(400, str(e))
        return result, 201


@api.route("/<string:name>/verify")
@api.param("name", "Backup filename")
class BackupVerify(Resource):
    @api.doc("verify_backup")
    @api.marshal_with(backup)
    @api.response(400, "Validation Error", error)
    def get(self, name):
        """Verify a backup file."""
        try:
            return verify_backup(name)
        except ValueError as e:
            api.abort(400, str(e))


@api.route("/<string:name>/restore")
@api.param("name", "Backup filename")
class BackupRestore(Resource):
    @api.doc("restore_backup")
    @api.marshal_with(backup)
    @api.response(400, "Validation Error", error)
    def post(self, name):
        """Restore database from a backup."""
        try:
            return restore_backup(name)
        except ValueError as e:
            api.abort(400, str(e))
