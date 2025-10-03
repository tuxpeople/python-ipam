"""Web UI routes for IPAM."""

import ipaddress

from flask import (
    Response,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from ipam.extensions import db
from ipam.forms import HostForm, ImportForm, NetworkForm
from ipam.models import Host, Network
from ipam.web import web_bp
from exporters import get_exporter, get_available_exporters
from importers import get_importer, get_available_importers


@web_bp.route("/")
def index():
    """Home page with overview."""
    networks_list = Network.query.all()
    hosts_list = Host.query.all()
    return render_template(
        "index.html", networks=networks_list, hosts=hosts_list
    )


@web_bp.route("/networks")
def networks():
    """Networks list page."""
    networks_list = Network.query.all()
    return render_template("networks.html", networks=networks_list)


@web_bp.route("/hosts")
def hosts():
    """Hosts list page."""
    hosts_list = Host.query.all()
    return render_template("hosts.html", hosts=hosts_list)


@web_bp.route("/add_network", methods=["GET", "POST"])
def add_network():
    """Add new network."""
    form = NetworkForm()
    if form.validate_on_submit():
        try:
            network_obj = ipaddress.IPv4Network(
                f"{form.network.data}/{form.cidr.data}", strict=False
            )
            broadcast = str(network_obj.broadcast_address)

            network = Network(
                network=form.network.data,
                cidr=form.cidr.data,
                broadcast_address=broadcast,
                name=form.name.data,
                domain=form.domain.data,
                vlan_id=form.vlan_id.data,
                description=form.description.data,
                location=form.location.data,
            )
            db.session.add(network)
            db.session.commit()
            flash("Network added successfully!", "success")
            return redirect(url_for("networks"))
        except ValueError as e:
            flash(f"Invalid network: {e}", "error")

    return render_template("add_network.html", form=form)


@web_bp.route("/add_host", methods=["GET", "POST"])
def add_host():
    """Add new host."""
    form = HostForm()
    form.network_id.choices = [(0, "Auto-detect")] + [
        (n.id, f"{n.network}/{n.cidr}") for n in Network.query.all()
    ]

    if form.validate_on_submit():
        network_id = form.network_id.data if form.network_id.data != 0 else None

        if not network_id:
            ip = ipaddress.IPv4Address(form.ip_address.data)
            for network in Network.query.all():
                net = ipaddress.IPv4Network(
                    f"{network.network}/{network.cidr}", strict=False
                )
                if ip in net:
                    network_id = network.id
                    break

        host = Host(
            ip_address=form.ip_address.data,
            hostname=form.hostname.data,
            cname=form.cname.data,
            mac_address=form.mac_address.data,
            description=form.description.data,
            status=form.status.data,
            network_id=network_id,
        )
        db.session.add(host)
        db.session.commit()
        flash("Host added successfully!", "success")
        return redirect(url_for("hosts"))

    return render_template("add_host.html", form=form)


@web_bp.route("/edit_network/<int:network_id>", methods=["GET", "POST"])
def edit_network(network_id):
    """Edit existing network."""
    network = Network.query.get_or_404(network_id)
    form = NetworkForm(obj=network)

    if form.validate_on_submit():
        try:
            network_obj = ipaddress.IPv4Network(
                f"{form.network.data}/{form.cidr.data}", strict=False
            )
            broadcast = str(network_obj.broadcast_address)

            network.network = form.network.data
            network.cidr = form.cidr.data
            network.broadcast_address = broadcast
            network.name = form.name.data
            network.domain = form.domain.data
            network.vlan_id = form.vlan_id.data
            network.description = form.description.data
            network.location = form.location.data

            db.session.commit()
            flash("Network updated successfully!", "success")
            return redirect(url_for("networks"))
        except ValueError as e:
            flash(f"Invalid network: {e}", "error")

    return render_template("edit_network.html", form=form, network=network)


@web_bp.route("/edit_host/<int:host_id>", methods=["GET", "POST"])
def edit_host(host_id):
    """Edit existing host."""
    host = Host.query.get_or_404(host_id)
    form = HostForm(obj=host)
    form.network_id.choices = [(0, "Auto-detect")] + [
        (n.id, f"{n.network}/{n.cidr}") for n in Network.query.all()
    ]

    if form.validate_on_submit():
        network_id = form.network_id.data if form.network_id.data != 0 else None

        if not network_id:
            ip = ipaddress.IPv4Address(form.ip_address.data)
            for network in Network.query.all():
                net = ipaddress.IPv4Network(
                    f"{network.network}/{network.cidr}", strict=False
                )
                if ip in net:
                    network_id = network.id
                    break

        host.ip_address = form.ip_address.data
        host.hostname = form.hostname.data
        host.cname = form.cname.data
        host.mac_address = form.mac_address.data
        host.description = form.description.data
        host.status = form.status.data
        host.network_id = network_id

        db.session.commit()
        flash("Host updated successfully!", "success")
        return redirect(url_for("hosts"))

    return render_template("edit_host.html", form=form, host=host)


@web_bp.route("/delete_network/<int:network_id>", methods=["POST"])
def delete_network(network_id):
    """Delete network."""
    network = Network.query.get_or_404(network_id)

    # Check if network has hosts
    if network.hosts:
        flash(
            f"Cannot delete network: {len(network.hosts)} hosts are still "
            f"assigned to this network",
            "error",
        )
        return redirect(url_for("networks"))

    db.session.delete(network)
    db.session.commit()
    flash("Network deleted successfully!", "success")
    return redirect(url_for("networks"))


@web_bp.route("/delete_host/<int:host_id>", methods=["POST"])
def delete_host(host_id):
    """Delete host."""
    host = Host.query.get_or_404(host_id)
    db.session.delete(host)
    db.session.commit()
    flash("Host deleted successfully!", "success")
    return redirect(url_for("hosts"))


@web_bp.route("/api/networks")
def api_networks():
    """Legacy API endpoint for networks (JSON)."""
    networks_list = Network.query.all()
    return jsonify(
        [
            {
                "id": n.id,
                "network": n.network,
                "cidr": n.cidr,
                "broadcast_address": n.broadcast_address,
                "name": n.name,
                "domain": n.domain,
                "vlan_id": n.vlan_id,
                "description": n.description,
                "location": n.location,
                "total_hosts": n.total_hosts,
                "used_hosts": n.used_hosts,
                "available_hosts": n.available_hosts,
            }
            for n in networks_list
        ]
    )


@web_bp.route("/api/hosts")
def api_hosts():
    """Legacy API endpoint for hosts (JSON)."""
    hosts_list = Host.query.all()
    return jsonify(
        [
            {
                "id": h.id,
                "ip_address": h.ip_address,
                "hostname": h.hostname,
                "cname": h.cname,
                "mac_address": h.mac_address,
                "description": h.description,
                "status": h.status,
                "network_id": h.network_id,
            }
            for h in hosts_list
        ]
    )


@web_bp.route("/export/<export_type>/<format_name>")
def export_data(export_type, format_name):
    """Export data in specified format."""
    try:
        exporter = get_exporter(format_name)

        if export_type == "networks":
            networks_list = Network.query.all()
            data = exporter.export_networks(networks_list)
            filename = f"networks.{exporter.file_extension}"
        elif export_type == "hosts":
            hosts_list = Host.query.all()
            data = exporter.export_hosts(hosts_list)
            filename = f"hosts.{exporter.file_extension}"
        else:
            flash("Invalid export type", "error")
            return redirect(url_for("index"))

        return Response(
            data,
            mimetype=exporter.mime_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except ValueError as e:
        flash(f"Export failed: {str(e)}", "error")
        return redirect(url_for("index"))


# Legacy routes for backward compatibility
@web_bp.route("/export/networks")
def export_networks_csv():
    """Legacy route for CSV export of networks."""
    return redirect(
        url_for("export_data", export_type="networks", format_name="csv")
    )


@web_bp.route("/export/hosts")
def export_hosts_csv():
    """Legacy route for CSV export of hosts."""
    return redirect(
        url_for("export_data", export_type="hosts", format_name="csv")
    )


@web_bp.route("/import", methods=["GET", "POST"])
def import_data():
    """Import networks or hosts from file."""
    form = ImportForm()

    # Populate format choices
    available_importers = get_available_importers()
    form.format_type.choices = [
        (name, importer.format_name)
        for name, importer in available_importers.items()
    ]

    if form.validate_on_submit():
        file_obj = form.file.data
        import_type = form.import_type.data
        format_type = form.format_type.data

        try:
            # Get importer
            importer = get_importer(format_type)

            # Read file content
            file_content = file_obj.read()

            # Import and validate data
            if import_type == "networks":
                raw_data = importer.import_networks(file_content)
                valid_data, errors = importer.validate_networks_data(raw_data)
                imported_count = _create_networks_from_data(valid_data)

                if errors:
                    flash(
                        f"Import completed with {len(errors)} errors. "
                        f"Check the data.",
                        "warning",
                    )
                    for error in errors[:5]:  # Show first 5 errors
                        flash(error, "warning")

                flash(
                    f"Successfully imported {imported_count} networks!",
                    "success",
                )
                return redirect(url_for("networks"))

            elif import_type == "hosts":
                raw_data = importer.import_hosts(file_content)
                valid_data, errors = importer.validate_hosts_data(raw_data)
                imported_count = _create_hosts_from_data(valid_data)

                if errors:
                    flash(
                        f"Import completed with {len(errors)} errors. "
                        f"Check the data.",
                        "warning",
                    )
                    for error in errors[:5]:  # Show first 5 errors
                        flash(error, "warning")

                flash(
                    f"Successfully imported {imported_count} hosts!", "success"
                )
                return redirect(url_for("hosts"))

        except Exception as e:
            flash(f"Import failed: {str(e)}", "error")

    return render_template("import_data.html", form=form)


# Legacy route for backward compatibility
@web_bp.route("/import_csv", methods=["GET", "POST"])
def import_csv():
    """Legacy route for CSV import."""
    return redirect(url_for("import_data"))


def _create_networks_from_data(networks_data):
    """Create Network objects from validated data."""
    imported_count = 0

    for network_data in networks_data:
        # Check if network already exists
        existing_network = Network.query.filter_by(
            network=network_data["network"]
        ).first()
        if existing_network:
            continue

        network = Network(
            network=network_data["network"],
            cidr=network_data["cidr"],
            broadcast_address=network_data["broadcast_address"],
            vlan_id=network_data.get("vlan_id"),
            location=network_data.get("location", ""),
            description=network_data.get("description", ""),
        )

        db.session.add(network)
        imported_count += 1

    db.session.commit()
    return imported_count


def _create_hosts_from_data(hosts_data):
    """Create Host objects from validated data."""
    imported_count = 0

    for host_data in hosts_data:
        # Check if host already exists
        existing_host = Host.query.filter_by(
            ip_address=host_data["ip_address"]
        ).first()
        if existing_host:
            continue

        # Auto-detect network
        network_id = None
        ip = ipaddress.IPv4Address(host_data["ip_address"])
        for network in Network.query.all():
            net = ipaddress.IPv4Network(
                f"{network.network}/{network.cidr}", strict=False
            )
            if ip in net:
                network_id = network.id
                break

        host = Host(
            ip_address=host_data["ip_address"],
            hostname=host_data.get("hostname", ""),
            mac_address=host_data.get("mac_address", ""),
            status=host_data.get("status", "active"),
            description=host_data.get("description", ""),
            network_id=network_id,
        )

        db.session.add(host)
        imported_count += 1

    db.session.commit()
    return imported_count
