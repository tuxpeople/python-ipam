import ipaddress
import os

from dotenv import load_dotenv
from exporters import get_exporter, register_exporter, get_available_exporters
from exporters.csv_exporter import CSVExporter
from exporters.json_exporter import JSONExporter
from importers import (
    get_importer,
    register_importer,
    get_available_importers,
    detect_format_by_extension,
)
from importers.csv_importer import CSVImporter
from flask import (
    Flask,
    Response,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import (
    FileField,
    IntegerField,
    SelectField,
    StringField,
    TextAreaField,
)
from wtforms.validators import DataRequired, IPAddress, Optional

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:///ipam.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Register export/import plugins
register_exporter("csv", CSVExporter())
register_exporter("json", JSONExporter())
register_importer("csv", CSVImporter())


class Network(db.Model):
    __tablename__ = "networks"

    id = db.Column(db.Integer, primary_key=True)
    network = db.Column(db.String(18), nullable=False, unique=True)
    cidr = db.Column(db.Integer, nullable=False)
    broadcast_address = db.Column(db.String(15))
    vlan_id = db.Column(db.Integer)
    description = db.Column(db.Text)
    location = db.Column(db.String(100))

    hosts = db.relationship(
        "Host", backref="network_ref", lazy=True, cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Network {self.network}/{self.cidr}>"

    @property
    def network_address(self):
        network = ipaddress.IPv4Network(
            f"{self.network}/{self.cidr}", strict=False
        )
        return str(network.network_address)

    @property
    def total_hosts(self):
        network = ipaddress.IPv4Network(
            f"{self.network}/{self.cidr}", strict=False
        )
        return len(list(network.hosts()))

    @property
    def used_hosts(self):
        return len(self.hosts)

    @property
    def available_hosts(self):
        return self.total_hosts - self.used_hosts


class Host(db.Model):
    __tablename__ = "hosts"

    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(15), nullable=False, unique=True)
    hostname = db.Column(db.String(255))
    mac_address = db.Column(db.String(17))
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default="active")
    network_id = db.Column(
        db.Integer, db.ForeignKey("networks.id"), nullable=True
    )

    def __repr__(self):
        return f"<Host {self.ip_address}>"


class NetworkForm(FlaskForm):
    network = StringField("Network Address", validators=[DataRequired()])
    cidr = IntegerField("CIDR", validators=[DataRequired()])
    vlan_id = IntegerField("VLAN ID", validators=[Optional()])
    description = TextAreaField("Description")
    location = StringField("Location")


class HostForm(FlaskForm):
    ip_address = StringField(
        "IP Address", validators=[DataRequired(), IPAddress()]
    )
    hostname = StringField("Hostname")
    mac_address = StringField("MAC Address")
    description = TextAreaField("Description")
    status = SelectField(
        "Status",
        choices=[
            ("active", "Active"),
            ("inactive", "Inactive"),
            ("reserved", "Reserved"),
        ],
    )
    network_id = SelectField("Network", coerce=int, validators=[Optional()])


class ImportForm(FlaskForm):
    file = FileField("File", validators=[DataRequired()])
    import_type = SelectField(
        "Import Type",
        choices=[("networks", "Networks"), ("hosts", "Hosts")],
        validators=[DataRequired()],
    )
    format_type = SelectField(
        "Format",
        choices=[],  # Will be populated dynamically
        validators=[DataRequired()],
    )


@app.route("/")
def index():
    networks_list = Network.query.all()
    hosts_list = Host.query.all()
    return render_template(
        "index.html", networks=networks_list, hosts=hosts_list
    )


@app.route("/networks")
def networks():
    networks_list = Network.query.all()
    return render_template("networks.html", networks=networks_list)


@app.route("/hosts")
def hosts():
    hosts_list = Host.query.all()
    return render_template("hosts.html", hosts=hosts_list)


@app.route("/add_network", methods=["GET", "POST"])
def add_network():
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


@app.route("/add_host", methods=["GET", "POST"])
def add_host():
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


@app.route("/api/networks")
def api_networks():
    networks_list = Network.query.all()
    return jsonify(
        [
            {
                "id": n.id,
                "network": n.network,
                "cidr": n.cidr,
                "broadcast_address": n.broadcast_address,
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


@app.route("/api/hosts")
def api_hosts():
    hosts_list = Host.query.all()
    return jsonify(
        [
            {
                "id": h.id,
                "ip_address": h.ip_address,
                "hostname": h.hostname,
                "mac_address": h.mac_address,
                "description": h.description,
                "status": h.status,
                "network_id": h.network_id,
            }
            for h in hosts_list
        ]
    )


@app.route("/export/<export_type>/<format_name>")
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
@app.route("/export/networks")
def export_networks_csv():
    """Legacy route for CSV export of networks."""
    return redirect(
        url_for("export_data", export_type="networks", format_name="csv")
    )


@app.route("/export/hosts")
def export_hosts_csv():
    """Legacy route for CSV export of hosts."""
    return redirect(
        url_for("export_data", export_type="hosts", format_name="csv")
    )


@app.route("/import", methods=["GET", "POST"])
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
                        f"Import completed with {len(errors)} errors. Check the data.",
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
                        f"Import completed with {len(errors)} errors. Check the data.",
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
@app.route("/import_csv", methods=["GET", "POST"])
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


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, host="0.0.0.0")
