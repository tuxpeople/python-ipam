# IPAM REST API Documentation

## Overview

The IPAM REST API provides programmatic access to all IP Address Management functionality with full CRUD operations, filtering, pagination, and interactive Swagger UI documentation.

**Status**: ✅ **Fully Implemented and Production-Ready**

## API Base URL

```
http://localhost:5000/api/v1
```

## Interactive Documentation

Access the interactive Swagger UI at:
```
http://localhost:5000/api/v1/docs
```

The Swagger UI provides:
- Complete API reference with request/response schemas
- Interactive "Try it out" functionality
- Request/response examples
- Model definitions

## Authentication

API requests require a token when `API_TOKENS` is configured.

**Headers**:
- `Authorization: Bearer <token>` (preferred)
- `X-API-Key: <token>` (alternative)

Requests without a valid token return `401 Unauthorized`.
Authentication is disabled when `API_TOKENS` is empty.

## Rate Limiting

Rate limits apply to API endpoints when `RATELIMIT_ENABLED=true`.
Default limit: `200 per minute` (configurable via `API_RATE_LIMIT`).
Use `RATELIMIT_STORAGE_URI` to configure the limiter backend. For
multi-process or multi-pod deployments, use a shared backend like Redis.

## Getting Started

### Starting the API Server

```bash
# Initialize database (first time only)
export FLASK_APP=app.py
flask db upgrade

# Start the development server
python app.py
```

The API will be available at `http://localhost:5000/api/v1`

## API Endpoints

### Networks

#### List Networks
```http
GET /api/v1/networks
```

**Query Parameters**:
- `page` (int, default: 1) - Page number
- `per_page` (int, default: 50) - Items per page
- `name` (string) - Filter by network name
- `domain` (string) - Filter by domain
- `vlan_id` (int) - Filter by VLAN ID
- `location` (string) - Filter by location

**Response**:
```json
{
  "data": [
    {
      "id": 1,
      "network": "192.168.1.0",
      "cidr": 24,
      "broadcast_address": "192.168.1.255",
      "name": "Office Network",
      "domain": "office.local",
      "vlan_id": 100,
      "description": "Main office network",
      "location": "Building A",
      "total_hosts": 254,
      "used_hosts": 45,
      "available_hosts": 209
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total_items": 1,
    "total_pages": 1
  }
}
```

#### Get Network
```http
GET /api/v1/networks/{id}
```

**Response**: Single network object (same structure as list item)

#### Create Network
```http
POST /api/v1/networks
Content-Type: application/json

{
  "network": "10.0.0.0",
  "cidr": 16,
  "name": "Corporate Network",
  "domain": "corp.local",
  "vlan_id": 200,
  "description": "Corporate network",
  "location": "HQ"
}
```

`network` accepts any host IP within the network, not just its base
address, and is normalized before saving (for example, `10.0.0.42`
with `cidr: 16` is stored as `10.0.0.0`). Creating a network that
overlaps an existing one (a subnet, supernet, or any other partial
overlap) is rejected (HTTP 400); networks may not overlap.

**Response**: Created network object (HTTP 201)

#### Update Network
```http
PUT /api/v1/networks/{id}
Content-Type: application/json

{
  "network": "10.0.0.0",
  "cidr": 16,
  "name": "Updated Name",
  "domain": "corp.local",
  "vlan_id": 200,
  "description": "Updated description",
  "location": "HQ"
}
```

`network` is normalized the same way as on create. `cidr` may not be
changed (HTTP 400); delete and recreate the network if it needs a
different CIDR. Moving the network's address onto a range that
overlaps another existing network is rejected the same way as on
create.

**Response**: Updated network object

#### Upsert Network
```http
POST /api/v1/networks/upsert
Content-Type: application/json

{
  "network": "10.0.0.0",
  "cidr": 16,
  "name": "Corporate Network",
  "domain": "corp.local",
  "vlan_id": 200,
  "description": "Corporate network",
  "location": "HQ"
}
```

Creates a network if none with this `network` address exists yet,
otherwise updates it. `network` and `cidr` are required, and `network`
is normalized the same way as on create (matched against the
normalized address). Only fields present in the request body are
changed; fields left out are kept as-is on an existing network.
Sending a field with an explicit `null` clears it. Changing `cidr` on
an existing network is rejected (HTTP 400), as is creating a network
that overlaps an existing one.

This endpoint does not use schema validation (unlike `POST` and `PUT`
above), since schema validation would reject an explicit `null` on a
typed field.

**Response**: Network object, HTTP 201 if created or HTTP 200 if
updated

#### Delete Network
```http
DELETE /api/v1/networks/{id}
```

**Response**: HTTP 204 (No Content)
**Error**: HTTP 400 if network has assigned hosts

#### Get Network Hosts
```http
GET /api/v1/networks/{id}/hosts
```

**Response**:
```json
{
  "network_id": 1,
  "network": "192.168.1.0/24",
  "hosts": [
    {
      "id": 1,
      "ip_address": "192.168.1.10",
      "hostname": "server01",
      "cname": "web",
      "mac_address": "aa:bb:cc:dd:ee:ff",
      "status": "active",
      "is_assigned": true,
      "last_seen": "2025-12-28T10:01:58",
      "discovery_source": "nmap",
      "description": "Web server"
    }
  ]
}
```

### Hosts

#### List Hosts
```http
GET /api/v1/hosts
```

**Query Parameters**:
- `page` (int, default: 1) - Page number
- `per_page` (int, default: 50) - Items per page
- `hostname` (string) - Filter by hostname (wildcard supported)
- `cname` (string) - Filter by CNAME
- `status` (string) - Filter by status (active, inactive, reserved)
- `is_assigned` (bool) - Filter by assignment status
- `mac_address` (string) - Filter by MAC address
- `network_id` (int) - Filter by network ID

**Response**:
```json
{
  "data": [
    {
      "id": 1,
      "ip_address": "192.168.1.10",
      "hostname": "server01",
      "cname": "web",
      "mac_address": "aa:bb:cc:dd:ee:ff",
      "status": "active",
      "is_assigned": true,
      "last_seen": "2025-12-28T10:01:58",
      "discovery_source": "nmap",
      "description": "Web server",
      "network_id": 1,
      "network": "192.168.1.0/24"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total_items": 1,
    "total_pages": 1
  }
}
```

#### Get Host
```http
GET /api/v1/hosts/{id}
```

**Response**: Single host object

#### Create Host
```http
POST /api/v1/hosts
Content-Type: application/json

{
  "ip_address": "192.168.1.100",
  "hostname": "server02",
  "cname": "api",
  "mac_address": "11:22:33:44:55:66",
  "status": "active",
  "is_assigned": true,
  "last_seen": "2025-12-28T10:01:58",
  "discovery_source": "nmap",
  "description": "API server",
  "network_id": 1
}
```

**Notes**:
- If `network_id` is omitted, the system auto-detects the network based on IP address.
- If `is_assigned` is omitted, the default is controlled by `HOST_ASSIGN_ON_CREATE`.
- If `hostname` ends with the resolved network's `domain` (the given or
  auto-detected one), that suffix is stripped before saving, e.g.
  `server02.corp.local` becomes `server02` for a network with domain
  `corp.local`.

**Response**: Created host object (HTTP 201)

#### Update Host
```http
PUT /api/v1/hosts/{id}
Content-Type: application/json

{
  "ip_address": "192.168.1.100",
  "hostname": "server02-updated",
  "cname": "api",
  "mac_address": "11:22:33:44:55:66",
  "status": "active",
  "is_assigned": true,
  "last_seen": "2025-12-28T10:01:58",
  "discovery_source": "nmap",
  "description": "Updated description",
  "network_id": 1
}
```

`hostname` has a matching network domain suffix stripped the same way
as on create, based on the resolved network (the given `network_id`,
or the current association if omitted).

**Response**: Updated host object

#### Upsert Host
```http
POST /api/v1/hosts/upsert
Content-Type: application/json

{
  "ip_address": "192.168.1.100",
  "hostname": "server02",
  "mac_address": "11:22:33:44:55:66",
  "status": "active",
  "last_seen": "2025-12-28T10:01:58",
  "discovery_source": "nmap"
}
```

Creates a host if none with this `ip_address` exists yet, otherwise
updates it. `ip_address` is required. Only fields present in the
request body are changed; fields left out are kept as-is on an
existing host (e.g. a manually curated `cname` or `description`
survives a discovery-driven upsert that doesn't know about it).
Sending a field with an explicit `null` clears it.

If `network_id` is omitted, it is auto-detected from the IP address
when a new host is created; on an update, an omitted `network_id`
leaves the host's current network association untouched. `hostname`
has a matching domain suffix of the resolved network stripped the
same way as on `POST`/`PUT`.

This endpoint does not use schema validation (unlike `POST` and `PUT`
above), since schema validation would reject an explicit `null` on a
typed field.

**Response**: Host object, HTTP 201 if created or HTTP 200 if updated

#### Delete Host
```http
DELETE /api/v1/hosts/{id}
```

**Response**: HTTP 204 (No Content)

### DHCP Ranges

#### List DHCP Ranges
```http
GET /api/v1/dhcp-ranges
```

**Query Parameters**:
- `page` (int, default: 1) - Page number
- `per_page` (int, default: 50) - Items per page
- `network_id` (int) - Filter by network ID

**Response**:
```json
{
  "data": [
    {
      "id": 1,
      "network_id": 1,
      "start_ip": "192.168.1.100",
      "end_ip": "192.168.1.150",
      "description": "Office DHCP pool",
      "is_active": true
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total_items": 1,
    "total_pages": 1
  }
}
```

#### Create DHCP Range
```http
POST /api/v1/dhcp-ranges
Content-Type: application/json

{
  "network_id": 1,
  "start_ip": "192.168.1.100",
  "end_ip": "192.168.1.150",
  "description": "Office DHCP pool",
  "is_active": true
}
```

**Response**: Created DHCP range object (HTTP 201)

#### Get DHCP Range
```http
GET /api/v1/dhcp-ranges/{id}
```

**Response**: Single DHCP range object

#### Update DHCP Range
```http
PUT /api/v1/dhcp-ranges/{id}
Content-Type: application/json

{
  "network_id": 1,
  "start_ip": "192.168.1.110",
  "end_ip": "192.168.1.160",
  "description": "Updated DHCP pool",
  "is_active": false
}
```

**Response**: Updated DHCP range object

#### Upsert DHCP Range
```http
POST /api/v1/dhcp-ranges/upsert
Content-Type: application/json

{
  "network_id": 1,
  "start_ip": "192.168.1.100",
  "end_ip": "192.168.1.150",
  "description": "Office DHCP pool",
  "is_active": true
}
```

Creates a DHCP range if none with this `(network_id, start_ip)` exists
yet, otherwise updates it. `start_ip` and `end_ip` are always required
since they define the range; `network_id` may be omitted, in which
case it is auto-detected from `start_ip` (the request fails with HTTP
400 if no network contains it). `description` is only changed when
present in the request body; leaving it out keeps the existing value,
and an explicit `null` clears it.

This endpoint does not use schema validation (unlike `POST` and `PUT`
above), since schema validation would reject an explicit `null` on a
typed field.

**Response**: DHCP range object, HTTP 201 if created or HTTP 200 if
updated

#### Delete DHCP Range
```http
DELETE /api/v1/dhcp-ranges/{id}
```

**Response**: HTTP 204 (No Content)

#### Network DHCP Ranges
```http
GET /api/v1/networks/{id}/dhcp-ranges
```

**Response**:
```json
{
  "data": [
    {
      "id": 1,
      "network_id": 1,
      "start_ip": "192.168.1.100",
      "end_ip": "192.168.1.150",
      "description": "Office DHCP pool",
      "is_active": true
    }
  ]
}
```

### Backups

#### List Backups
```http
GET /api/v1/backups
```

**Query Parameters**:
- `page` (int, default: 1) - Page number
- `per_page` (int, default: 50) - Items per page

**Response**:
```json
{
  "data": [
    {
      "name": "ipam-backup-20251228-120000Z.db",
      "size_bytes": 40960,
      "created_at": "2025-12-28T12:00:00+00:00"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total_items": 1,
    "total_pages": 1
  }
}
```

#### Create Backup
```http
POST /api/v1/backups
```

**Response**: Created backup object (HTTP 201)

#### Verify Backup
```http
GET /api/v1/backups/{name}/verify
```

**Response**:
```json
{
  "name": "ipam-backup-20251228-120000Z.db",
  "integrity_ok": true,
  "integrity_message": "ok"
}
```

#### Restore Backup
```http
POST /api/v1/backups/{name}/restore
```

**Response**:
```json
{
  "name": "ipam-backup-20251228-120000Z.db",
  "restored": true,
  "integrity_ok": true,
  "integrity_message": "ok"
}
```

### IP Management

#### Get Next Available IP
```http
GET /api/v1/ip/networks/{network_id}/next-ip
```

**Response**:
```json
{
  "ip_address": "192.168.1.45",
  "network": "192.168.1.0/24",
  "network_id": 1
}
```

**Error**: HTTP 400 if no available IPs

#### Get Available IPs
```http
GET /api/v1/ip/networks/{network_id}/available-ips?limit=10
```

**Query Parameters**:
- `limit` (int, optional) - Limit number of IPs returned
Note: Active DHCP ranges are excluded from available IPs.

**Response**:
```json
{
  "network": "192.168.1.0/24",
  "network_id": 1,
  "total_available": 209,
  "available_ips": [
    "192.168.1.11",
    "192.168.1.12",
    "..."
  ]
}
```

#### Query IP Address
```http
GET /api/v1/ip/{ip_address}
```

**Example**: `GET /api/v1/ip/192.168.1.10`

**Response (Assigned)**:
```json
{
  "ip_address": "192.168.1.10",
  "status": "assigned",
  "host": {
    "id": 1,
    "hostname": "server01",
    "cname": "web",
    "mac_address": "aa:bb:cc:dd:ee:ff",
    "status": "active",
    "is_assigned": true,
    "last_seen": "2025-12-28T10:01:58",
    "discovery_source": "nmap",
    "description": "Web server",
    "network_id": 1,
    "network": "192.168.1.0/24"
  }
}
```

**Response (Available)**:
```json
{
  "ip_address": "192.168.1.45",
  "status": "available",
  "network": {
    "id": 1,
    "network": "192.168.1.0/24",
    "name": "Office Network",
    "domain": "office.local",
    "vlan_id": 100,
    "location": "Building A"
  }
}
```

**Response (DHCP Range)**:
```json
{
  "ip_address": "192.168.1.120",
  "status": "dhcp",
  "dhcp_range": {
    "id": 1,
    "start_ip": "192.168.1.100",
    "end_ip": "192.168.1.150",
    "network_id": 1
  },
  "network": {
    "id": 1,
    "network": "192.168.1.0/24",
    "name": "Office Network",
    "domain": "office.local",
    "vlan_id": 100,
    "location": "Building A"
  }
}
```

**Response (Unmanaged)**:
```json
{
  "ip_address": "8.8.8.8",
  "status": "unmanaged",
  "message": "IP address is not in any managed network"
}
```

## Error Responses

All errors follow this format:

```json
{
  "message": "Error description",
  "errors": {
    "field": "Detailed error information"
  }
}
```

**Common HTTP Status Codes**:
- `200 OK` - Successful GET/PUT request
- `201 Created` - Successful POST request
- `204 No Content` - Successful DELETE request
- `400 Bad Request` - Validation error or business logic error
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

## Examples

### cURL Examples

**List all active hosts in a network**:
```bash
curl "http://localhost:5000/api/v1/hosts?status=active&network_id=1"
```

**Create a network**:
```bash
curl -X POST http://localhost:5000/api/v1/networks \
  -H "Content-Type: application/json" \
  -d '{
    "network": "10.1.0.0",
    "cidr": 24,
    "name": "Test Network",
    "vlan_id": 300
  }'
```

**Get next available IP**:
```bash
curl "http://localhost:5000/api/v1/ip/networks/1/next-ip"
```

**Filter networks by location**:
```bash
curl "http://localhost:5000/api/v1/networks?location=datacenter&page=1&per_page=20"
```

### Python Example

```python
import requests

BASE_URL = "http://localhost:5000/api/v1"

# Get next available IP
response = requests.get(f"{BASE_URL}/ip/networks/1/next-ip")
next_ip = response.json()["ip_address"]

# Create host with that IP
host_data = {
    "ip_address": next_ip,
    "hostname": "new-server",
    "mac_address": "aa:bb:cc:dd:ee:ff",
    "status": "active",
    "network_id": 1
}
response = requests.post(f"{BASE_URL}/hosts", json=host_data)
created_host = response.json()
print(f"Created host: {created_host['hostname']} with IP {created_host['ip_address']}")
```

## Implementation Status

**Completed**:
- ✅ All endpoint implementations, including upsert for networks/hosts
- ✅ Request/response models
- ✅ Filtering and pagination
- ✅ Swagger UI integration
- ✅ Input validation
- ✅ Error handling
- ✅ API authentication
- ✅ Rate limiting
- ✅ API tests

The circular import issue that previously blocked this (see
REFACTORING.md for the historical write-up) has been resolved.

## Next Steps

1. **Performance tuning** - Query optimization for large datasets
2. **API versioning** - Support for future API versions

## Related Documentation

- **FEATURES.md**: Feature roadmap and requirements (IPAM-023)
- **REFACTORING.md**: Detailed refactoring plan
- **CLAUDE.md**: Project coding standards
