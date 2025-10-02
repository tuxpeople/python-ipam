import ipaddress
import os

from dotenv import load_dotenv
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    url_for,
)
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import IntegerField, SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, IPAddress, Optional

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:///ipam.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


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


@app.route("/")
def index():
    networks_list = Network.query.all()
    hosts_list = Host.query.all()
    return render_template("index.html", networks=networks_list, hosts=hosts_list)


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


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, host="0.0.0.0")
