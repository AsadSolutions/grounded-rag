# Atlas Product Overview

**Product:** Atlas by TechCorp, Inc.
**Current version:** v4.2, codename "Fernbank"
**Document reference:** DOC-3001
**Owner:** Product Team

## What Atlas is

Atlas is a workflow and project management platform built by TechCorp, Inc., founded in 2015 and headquartered in Cedar Harbor. Atlas helps teams plan work in Boards, automate repetitive processes in Workflows, track progress in Reports, and connect to other tools through Integrations. Atlas is available as a web application and as native desktop apps for macOS and Windows.

## Core modules

Atlas is organized around four core modules:

- **Boards:** a flexible task and project view supporting list, kanban, and calendar layouts.
- **Workflows:** automation rules that move tasks between states, assign owners, and trigger notifications based on conditions a team defines.
- **Reports:** dashboards summarizing throughput, cycle time, and workload across Boards.
- **Integrations:** connections to third-party tools such as chat platforms, calendars, and file storage, configured through the Atlas API described in the API Basics guide.

## Release and versioning

Atlas follows a monthly minor release cadence, with major versions released roughly once a year. The current major version is v4.2. Version numbers follow the pattern major.minor, so v4.2 indicates the fourth major release, second minor update. Each release, major or minor, is documented in the in-app changelog, and breaking changes are only introduced in major version releases.

## Plans and seat limits

Atlas is offered in four plans, each with a defined seat limit:

- **Starter:** up to 5 seats, priced at $12 per seat per month, includes Boards and Workflows.
- **Team:** up to 25 seats, priced at $24 per seat per month, adds Reports and Integrations.
- **Business:** up to 100 seats, priced at $39 per seat per month, adds single sign-on and advanced permission controls.
- **Enterprise:** unlimited seats, custom pricing, adds dedicated support and audit log export.

Workspaces that exceed their plan's seat limit are prompted to upgrade before additional teammates can be invited; existing seats are never removed automatically.

## Workspace roles

Every Atlas workspace has four default roles: Owner, Admin, Member, and Viewer. The Owner role is assigned automatically to whoever creates the workspace and can be transferred to another Admin. Admins can manage billing, integrations, and workspace-wide settings. Members can create and edit Boards they have access to. Viewers can see Boards shared with them but cannot make edits.

## Data residency

Enterprise and Business plan workspaces may choose between two data residency regions at workspace creation: United States or European Union. Starter and Team plan workspaces default to United States residency. Residency selection determines where workspace data, including file attachments, is stored at rest; it cannot be changed after workspace creation without opening a support request.

## Where to go next

New users should start with the Getting Started Guide to create a workspace and invite a team. Developers integrating with Atlas programmatically should read the API Basics guide. Anyone running into an unexpected error code should consult the Troubleshooting Guide. Questions about uptime commitments and cancellation terms are covered in the Warranty and Refund Policy, document reference DOC-3301. Questions about data protection are covered in the Security FAQ.

## Support

Every Atlas plan includes support, with response times that scale by tier. Standard support responds within 24 business hours. Business and above plans receive Priority support, responding within 4 hours. Enterprise plans receive 24-hour, 7-day coverage with a 1 hour first response target. Full SLA definitions are in the Troubleshooting Guide.

## Company background

TechCorp, Inc. was founded in 2015 in Cedar Harbor and has shipped Atlas continuously since its first public release. Atlas is used by teams ranging from 5-person startups on the Starter plan to large Enterprise customers with thousands of seats across multiple workspaces.
