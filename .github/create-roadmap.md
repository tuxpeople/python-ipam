# GitHub Roadmap Setup Instructions

This document explains how to create a GitHub Project roadmap and assign feature requests.

## Prerequisites

1. GitHub CLI (`gh`) installed and authenticated
2. Admin access to the repository
3. Feature issues created (run `.github/create-feature-issues.sh`)

## Step 1: Create Feature Issues

Run the script to create all feature issues from FEATURES.md:

```bash
cd /Volumes/development/github/tuxpeople/python-ipam
.github/create-feature-issues.sh
```

This will create 8 issues for the planned features:

- IPAM-010: Subnet Calculator
- IPAM-011: Network Scanner Integration
- IPAM-012: Advanced Import Formats
- IPAM-013: Advanced Export with Filtering
- IPAM-014: REST API Expansion
- IPAM-015: Hybrid Authentication System
- IPAM-016: Local User Management UI
- IPAM-017: Data Backup & Restore

## Step 2: Create Milestones

Create version milestones to organize features:

```bash
# Create v1.1.0 milestone (Q4 2025)
gh api repos/:owner/:repo/milestones \
  --method POST \
  --field title="v1.1.0" \
  --field description="Advanced export, network tools, enhanced imports, REST API expansion" \
  --field due_on="2025-12-31T23:59:59Z"

# Create v1.2.0 milestone (Q1 2026)
gh api repos/:owner/:repo/milestones \
  --method POST \
  --field title="v1.2.0" \
  --field description="Hybrid authentication, user management, role-based access control" \
  --field due_on="2026-03-31T23:59:59Z"

# Create v2.0.0 milestone (Q2 2026)
gh api repos/:owner/:repo/milestones \
  --method POST \
  --field title="v2.0.0" \
  --field description="Network discovery, advanced reporting, performance optimizations" \
  --field due_on="2026-06-30T23:59:59Z"
```

## Step 3: Assign Issues to Milestones

### v1.1.0 Issues

```bash
gh issue edit 5 --milestone "v1.1.0"  # Subnet Calculator
gh issue edit 6 --milestone "v1.1.0"  # Network Scanner
gh issue edit 7 --milestone "v1.1.0"  # Advanced Import Formats
gh issue edit 8 --milestone "v1.1.0"  # Advanced Export
gh issue edit 9 --milestone "v1.1.0"  # REST API Expansion
gh issue edit 12 --milestone "v1.1.0"  # Data Backup & Restore
```

### v1.2.0 Issues

```bash
gh issue edit 10 --milestone "v1.2.0"  # Hybrid Authentication
gh issue edit 11 --milestone "v1.2.0"  # User Management UI
```

## Step 4: Create GitHub Project (Roadmap)

### Via GitHub Web UI (Recommended)

1. Go to your repository on GitHub
2. Click on **Projects** tab
3. Click **New project**
4. Select **Roadmap** template
5. Name it "Python IPAM Roadmap"
6. Configure views:
   - **Roadmap View**: Timeline view by milestone
   - **Backlog View**: Table view of all planned features
   - **Status Board**: Kanban board (To Do, In Progress, Done)

### Add Issues to Project

1. In the project, click **Add items**
2. Search for issues labeled `enhancement`
3. Select all feature issues (IPAM-010 through IPAM-017)
4. Set status:
   - All planned features: **To Do**
5. Set iteration/timeline:
   - Group by milestone (v1.1.0, v1.2.0, v2.0.0)

### Configure Project Fields

Add custom fields to track:

- **Priority**: Low, Medium, High, Critical
- **Category**: Core, UI/UX, API, Security, Data Management, Network Tools
- **Estimated Effort**: Small (1-2d), Medium (2-4d), High (4-7d)
- **Dependencies**: Link to blocking issues

## Step 5: Configure Project Automation

Set up GitHub Actions workflow for automatic project updates:

```yaml
# .github/workflows/project-automation.yml
name: Project Automation

on:
  issues:
    types: [opened, closed, labeled]
  pull_request:
    types: [opened, closed, merged]

jobs:
  update-project:
    runs-on: ubuntu-latest
    steps:
      - name: Add to project
        uses: actions/add-to-project@v0.5.0
        with:
          project-url: https://github.com/users/<username>/projects/<project-number>
          github-token: ${{ secrets.PROJECT_TOKEN }}
          labeled: enhancement
```

## Step 6: Publish Roadmap

Make the roadmap public:

1. In project settings, ensure **Visibility** is set to **Public**
2. Add project link to README.md:

```markdown
## 📋 Roadmap

View our [feature roadmap](https://github.com/users/<username>/projects/<project-number>)
to see planned features and development timeline.
```

## Alternative: CLI-based Project Creation

If you prefer CLI-based approach:

```bash
# Create project
gh project create \
  --owner "@me" \
  --title "Python IPAM Roadmap" \
  --template "Roadmap"

# Add issues to project (get project ID from output above)
PROJECT_ID="<project-id>"

for issue in $(gh issue list --label "enhancement" --json number --jq '.[].number'); do
  gh project item-add $PROJECT_ID --owner "@me" --url "https://github.com/$(gh repo view --json nameWithOwner -q .nameWithOwner)/issues/$issue"
done
```

## Roadmap Structure

### v1.1.0 - Q4 2025 (Export/Import & Tools)

- IPAM-010: Subnet Calculator
- IPAM-011: Network Scanner Integration
- IPAM-012: Advanced Import Formats
- IPAM-013: Advanced Export with Filtering (High Priority)
- IPAM-014: REST API Expansion
- IPAM-017: Data Backup & Restore

### v1.2.0 - Q1 2026 (Authentication & Security)

- IPAM-015: Hybrid Authentication System (High Priority)
- IPAM-016: Local User Management UI

### v2.0.0 - Q2 2026 (Discovery & Analytics)

- Network discovery tools
- Advanced reporting and analytics
- Performance optimizations for large datasets

## Next Steps

1. Run `.github/create-feature-issues.sh` to create all issues
2. Create milestones for v1.1.0, v1.2.0, v2.0.0
3. Assign issues to appropriate milestones
4. Create GitHub Project using Roadmap template
5. Add all enhancement issues to the project
6. Configure project views and automation
7. Update README.md with roadmap link

## Maintenance

- Review roadmap monthly
- Update issue priorities based on user feedback
- Move completed features to "Done"
- Add new feature requests with proper labels and milestones
