"""WTForms for web UI."""

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    FileField,
    IntegerField,
    SelectField,
    StringField,
    TextAreaField,
)
from wtforms.validators import DataRequired, IPAddress, Optional


class NetworkForm(FlaskForm):
    """Network creation/edit form."""

    network = StringField("Network Address", validators=[DataRequired()])
    cidr = IntegerField("CIDR", validators=[DataRequired()])
    name = StringField("Network Name", validators=[Optional()])
    domain = StringField("Domain", validators=[Optional()])
    vlan_id = IntegerField("VLAN ID", validators=[Optional()])
    description = TextAreaField("Description")
    location = StringField("Location")


class HostForm(FlaskForm):
    """Host creation/edit form."""

    ip_address = StringField(
        "IP Address", validators=[DataRequired(), IPAddress()]
    )
    hostname = StringField("Hostname")
    cname = StringField("CNAME Alias")
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
    is_assigned = BooleanField("Assigned")
    network_id = SelectField("Network", coerce=int, validators=[Optional()])


class ImportForm(FlaskForm):
    """Data import form."""

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
