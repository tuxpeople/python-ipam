#!/bin/bash
# Script to create GitHub issues for planned features from FEATURES.md

# Check if gh CLI is available
if ! command -v gh &> /dev/null; then
    echo "Error: GitHub CLI (gh) is not installed. Please install it first:"
    echo "  brew install gh  # macOS"
    echo "  https://cli.github.com/manual/installation"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "Error: Not authenticated with GitHub CLI. Please run: gh auth login"
    exit 1
fi

echo "Creating GitHub issues for planned features..."
echo ""

# IPAM-010: Subnet Calculator
gh issue create \
  --title "[Feature] IPAM-010: Subnet Calculator" \
  --label "enhancement,network-tools" \
  --body "## Problem Description
Users need to calculate subnets, split networks, and check for IP range conflicts when planning their network infrastructure.

## Proposed Solution
Built-in subnet calculator and IP range tools integrated into the web interface.

## Acceptance Criteria
- Calculate available subnets from larger networks
- Visual subnet splitting recommendations
- IP range conflict detection
- Subnet mask conversion tools

## Feature Category
Network Management

## Priority
Medium

## Additional Context
**Technical Notes:**
- Use Python's ipaddress library for calculations
- Add JavaScript for real-time calculations
- Estimated effort: 2-3 days

**Feature ID:** IPAM-010
**Category:** Network Tools
**Version Target:** v1.1.0 (Q4 2025)"

echo "✓ Created issue for IPAM-010: Subnet Calculator"

# IPAM-011: Network Scanner Integration
gh issue create \
  --title "[Feature] IPAM-011: Network Scanner Integration" \
  --label "enhancement,discovery" \
  --body "## Problem Description
Manual host discovery and registration is time-consuming. Administrators need automated network scanning capabilities.

## Proposed Solution
Scan network ranges for active hosts and auto-populate the IPAM database with discovered devices.

## Acceptance Criteria
- Ping sweep functionality
- Port scanning for common services
- Auto-populate discovered hosts
- Scheduled scan capabilities

## Feature Category
Network Management

## Priority
Medium

## Additional Context
**Technical Notes:**
- Consider using python-nmap library
- Estimated effort: 4-5 days

**Dependencies:** IPAM-010 (Subnet Calculator)
**Feature ID:** IPAM-011
**Category:** Discovery
**Version Target:** v1.1.0 (Q4 2025)"

echo "✓ Created issue for IPAM-011: Network Scanner Integration"

# IPAM-012: Advanced Import Formats
gh issue create \
  --title "[Feature] IPAM-012: Advanced Import Formats" \
  --label "enhancement,import-export" \
  --body "## Problem Description
Users have data in various formats (XML, Excel, network tool exports) that need to be imported into Python IPAM.

## Proposed Solution
Extend the plugin-based import system to support XML, Excel, and network tool exports (Nmap, Cisco/HP switch MAC tables).

## Acceptance Criteria
- XML import/export
- Excel (.xlsx) support
- Nmap XML import
- Cisco/HP switch MAC table import

## Feature Category
Import/Export

## Priority
Low

## Additional Context
**Technical Notes:**
- Extends existing plugin system (IPAM-004)
- Estimated effort: 2-3 days

**Dependencies:** IPAM-004 (Extensible Import System)
**Feature ID:** IPAM-012
**Category:** Data Management
**Version Target:** v1.1.0 (Q4 2025)"

echo "✓ Created issue for IPAM-012: Advanced Import Formats"

# IPAM-013: Advanced Export with Filtering
gh issue create \
  --title "[Feature] IPAM-013: Advanced Export with Filtering" \
  --label "enhancement,import-export" \
  --body "## Problem Description
Users need to export specific subsets of data based on various criteria (VLAN, location, status, date ranges) rather than exporting all data.

## Proposed Solution
Advanced export functionality with filtering options, custom field selection, and export templates.

## Acceptance Criteria
- **Complete Database Export**: All networks, hosts, and relationships
- **Filtered Network Export**: By VLAN, location, IP range, utilization
- **Filtered Host Export**: By status, network, hostname pattern, date range
- **Multiple Format Support**: CSV, JSON, Excel for all export types
- **Custom Field Selection**: Choose which columns to include
- **Export Templates**: Save and reuse filter configurations

## UI Features
- Advanced filter interface with multiple criteria
- Export preview with row count estimation
- Progress indicator for large exports
- Download history and re-export capability

## Feature Category
Import/Export

## Priority
High

## Additional Context
**Technical Implementation:**
\`\`\`
# Export with advanced filtering
/export/networks?vlan_id=100&location=datacenter&format=csv
/export/hosts?status=active&network_id=5&format=json
/export/complete?include=networks,hosts,relationships&format=excel
\`\`\`

**Dependencies:** IPAM-004 (Extensible Export System)
**Feature ID:** IPAM-013
**Category:** Data Management
**Estimated Effort:** 2-3 days
**Version Target:** v1.1.0 (Q4 2025)"

echo "✓ Created issue for IPAM-013: Advanced Export with Filtering"

# IPAM-014: REST API Expansion
gh issue create \
  --title "[Feature] IPAM-014: REST API Expansion" \
  --label "enhancement,api" \
  --body "## Problem Description
The REST API needs authentication, rate limiting, and enhanced documentation for production use.

## Proposed Solution
Expand the existing REST API with authentication, rate limiting, and comprehensive OpenAPI/Swagger documentation.

## Acceptance Criteria
- CRUD operations for all resources
- API authentication (token-based)
- OpenAPI/Swagger documentation
- Rate limiting and pagination

## Feature Category
API

## Priority
Medium

## Additional Context
**Technical Notes:**
- Consider Flask-RESTX for auto-documentation
- Estimated effort: 3-4 days

**Dependencies:** IPAM-015 (Hybrid Authentication System)
**Feature ID:** IPAM-014
**Category:** API
**Version Target:** v1.1.0 (Q4 2025)

**Note:** Basic REST API (IPAM-023) is already complete. This feature adds authentication and rate limiting."

echo "✓ Created issue for IPAM-014: REST API Expansion"

# IPAM-015: Hybrid Authentication System
gh issue create \
  --title "[Feature] IPAM-015: Hybrid Authentication System" \
  --label "enhancement,security,authentication" \
  --body "## Problem Description
Production deployments need authentication and authorization. Small deployments need simple local user management, while enterprises need OIDC integration.

## Proposed Solution
Hybrid authentication system supporting both local user management and OIDC via OAuth2 Proxy, configurable via environment variables.

## Acceptance Criteria
- **Local Authentication**: Built-in user registration, login, password reset
- **OAuth2 Proxy Support**: OIDC integration via reverse proxy
- **Role-based Access Control**: Admin, User, ReadOnly roles
- **Configurable Auth Mode**: Environment variable to switch between modes
- **User Management UI**: Admin interface for local users
- **Session Management**: Secure session handling for both modes

## Authentication Modes

**Mode 1: Local Authentication (Default)**
\`\`\`python
# .env
AUTH_MODE=local
SECRET_KEY=your-secret-key
\`\`\`

**Mode 2: OAuth2 Proxy**
\`\`\`yaml
# docker-compose.auth.yml
services:
  oauth2-proxy:
    image: quay.io/oauth2-proxy/oauth2-proxy:latest
    environment:
      - OAUTH2_PROXY_UPSTREAM=http://ipam:5000
      - OAUTH2_PROXY_OIDC_ISSUER_URL=\${OIDC_ISSUER}
  ipam:
    environment:
      - AUTH_MODE=proxy
      - AUTH_USER_HEADER=X-Forwarded-User
\`\`\`

## Feature Category
Authentication/Authorization

## Priority
High

## Additional Context
**Technical Notes:**
- Use Flask-Login for local authentication
- Header extraction for proxy-based auth
- Unified User model supporting both auth types
- Estimated effort: 3-4 days

**Feature ID:** IPAM-015
**Category:** Security
**Version Target:** v1.2.0 (Q1 2026)

**Rationale:** Maximum flexibility - simple setup for development/small deployments, enterprise-ready OIDC for larger organizations"

echo "✓ Created issue for IPAM-015: Hybrid Authentication System"

# IPAM-016: Local User Management UI
gh issue create \
  --title "[Feature] IPAM-016: Local User Management UI" \
  --label "enhancement,ui,security" \
  --body "## Problem Description
Administrators need a user-friendly interface to manage local user accounts, roles, and permissions.

## Proposed Solution
Admin interface for local user management with user list, add/edit/disable functionality, and role assignment.

## Acceptance Criteria
- User list with search and filtering
- Add/edit/disable user accounts
- Role assignment interface
- Password reset functionality
- User activity logging

## Feature Category
User Interface

## Priority
Medium

## Additional Context
**Technical Notes:**
- Reuse existing Bootstrap/DataTables UI patterns
- Add password strength validation
- Implement user audit trail
- Estimated effort: 1-2 days

**Dependencies:** IPAM-015 (Hybrid Authentication System)
**Feature ID:** IPAM-016
**Category:** UI/Security
**Version Target:** v1.2.0 (Q1 2026)"

echo "✓ Created issue for IPAM-016: Local User Management UI"

# IPAM-017: Data Backup & Restore
gh issue create \
  --title "[Feature] IPAM-017: Data Backup & Restore" \
  --label "enhancement,data-management" \
  --body "## Problem Description
Users need automated backup capabilities and easy restore functionality to protect against data loss.

## Proposed Solution
Automated backup and restore functionality with scheduling, verification, and migration utilities.

## Acceptance Criteria
- Scheduled database backups
- One-click restore from backup
- Complete database migration utilities
- Backup verification and integrity checks

## Feature Category
Data Management

## Priority
Medium

## Additional Context
**Technical Notes:**
- Estimated effort: 1-2 days

**Feature ID:** IPAM-017
**Category:** Data Management
**Version Target:** v1.1.0 (Q4 2025)"

echo "✓ Created issue for IPAM-017: Data Backup & Restore"

echo ""
echo "=========================================="
echo "✓ Successfully created 8 feature issues"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Review the created issues at: https://github.com/$(gh repo view --json nameWithOwner -q .nameWithOwner)/issues"
echo "2. Create a GitHub Project roadmap"
echo "3. Assign issues to milestones (v1.1.0, v1.2.0, v2.0.0)"
echo ""
