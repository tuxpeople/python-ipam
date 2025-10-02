import pytest
from app import NetworkForm, HostForm


class TestNetworkForm:
    def test_valid_network_form(self):
        form_data = {
            "network": "192.168.1.0",
            "cidr": 24,
            "vlan_id": 100,
            "description": "Test network",
            "location": "Test location",
        }
        form = NetworkForm(data=form_data)
        assert form.validate()

    def test_network_form_required_fields(self):
        form_data = {}
        form = NetworkForm(data=form_data)
        assert not form.validate()
        assert "This field is required." in form.network.errors
        assert "This field is required." in form.cidr.errors

    def test_network_form_optional_fields(self):
        form_data = {"network": "192.168.1.0", "cidr": 24}
        form = NetworkForm(data=form_data)
        assert form.validate()


class TestHostForm:
    def test_valid_host_form(self):
        form_data = {
            "ip_address": "192.168.1.10",
            "hostname": "test-host",
            "mac_address": "aa:bb:cc:dd:ee:ff",
            "description": "Test host",
            "status": "active",
            "network_id": 1,
        }
        form = HostForm(data=form_data)
        assert form.validate()

    def test_host_form_required_ip(self):
        form_data = {"hostname": "test-host", "status": "active"}
        form = HostForm(data=form_data)
        assert not form.validate()
        assert "This field is required." in form.ip_address.errors

    def test_host_form_invalid_ip(self):
        form_data = {"ip_address": "invalid-ip", "status": "active"}
        form = HostForm(data=form_data)
        assert not form.validate()
        assert "Invalid IP address." in form.ip_address.errors

    def test_host_form_valid_ip_formats(self):
        valid_ips = ["192.168.1.1", "10.0.0.1", "172.16.0.1", "1.1.1.1"]

        for ip in valid_ips:
            form_data = {"ip_address": ip, "status": "active"}
            form = HostForm(data=form_data)
            assert form.validate(), f"IP {ip} should be valid"

    def test_host_form_invalid_ip_formats(self):
        invalid_ips = ["256.1.1.1", "192.168.1", "not-an-ip", "192.168.1.1.1"]

        for ip in invalid_ips:
            form_data = {"ip_address": ip, "status": "active"}
            form = HostForm(data=form_data)
            assert not form.validate(), f"IP {ip} should be invalid"

    def test_host_form_status_choices(self):
        valid_statuses = ["active", "inactive", "reserved"]

        for status in valid_statuses:
            form_data = {"ip_address": "192.168.1.10", "status": status}
            form = HostForm(data=form_data)
            assert form.validate(), f"Status {status} should be valid"

    def test_host_form_optional_fields(self):
        form_data = {"ip_address": "192.168.1.10", "status": "active"}
        form = HostForm(data=form_data)
        assert form.validate()
