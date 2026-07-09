# Atlas Security FAQ

**Product:** Atlas by TechCorp, Inc.
**Document reference:** DOC-3401
**Owner:** Security Team

## Is Atlas compliant with industry security standards?

Atlas is SOC 2 Type II compliant, audited annually by an independent third-party auditor. The current SOC 2 report is available to Business and Enterprise customers on request through the support portal, subject to a mutual non-disclosure agreement where required.

## How is my data encrypted?

Data at rest in Atlas is encrypted using AES-256. Data in transit, including all API traffic and web app traffic, is encrypted using TLS 1.3. Encryption keys are managed through a dedicated key management service and are rotated on a regular schedule that is independent of any customer action.

## Where is my data stored?

Business and Enterprise plan workspaces may choose a data residency region at workspace creation: United States or European Union, as described in the Product Overview. Starter and Team plan workspaces default to United States residency. Regardless of region, backups follow the same encryption and access control standards as primary data storage.

## How does authentication work?

Atlas accounts are protected by a password policy requiring a minimum of 12 characters, including at least 1 number and 1 symbol, matching the requirement described in the Getting Started Guide. Atlas supports multi-factor authentication using both TOTP authenticator apps and SMS-based codes. Business and Enterprise plans additionally support single sign-on through common identity providers.

## What happens if I'm inactive?

Web app sessions time out after 30 minutes of inactivity by default, requiring re-authentication. Business and Enterprise plan Admins can configure a custom session timeout between 15 and 60 minutes from workspace security settings. API authentication tokens, separate from web sessions, expire after 24 hours as described in the API Basics guide.

## How are API keys protected?

API keys are shown only once at creation time and are stored by TechCorp in hashed form, meaning TechCorp cannot retrieve a lost API key; a new one must be generated if a key is lost. API keys can be scoped to specific permissions and revoked instantly from workspace settings, which immediately invalidates any active tokens issued from that key.

## What is your breach notification process?

In the event of a confirmed security incident affecting customer data, TechCorp notifies affected customers within 72 hours of confirming the incident. Notification includes a description of the incident, the data categories affected, and recommended actions. Enterprise customers with a dedicated account representative are notified directly in addition to the standard notification channel.

## Can I run a security assessment against Atlas?

Business and Enterprise customers may request permission to run a security assessment or penetration test against their own workspace, subject to prior written approval from the Security Team and a defined testing window to avoid impacting other customers on shared infrastructure. Requests should be submitted at least 10 business days before the desired testing window.

## How does Atlas handle vulnerability reports?

TechCorp maintains a responsible disclosure program for security researchers. Reports can be submitted through the security contact listed in the support portal. Confirmed vulnerabilities are triaged by severity, with critical vulnerabilities addressed on an expedited timeline outside the normal release cadence described in the Product Overview.

## Where can I learn more about uptime and incident history?

Historical uptime and incident information is available on the Atlas status page. Service credit eligibility for uptime shortfalls is described in the Warranty and Refund Policy, document reference DOC-3301.

## Cross-references

- See the Getting Started Guide for the password policy referenced above.
- See the API Basics guide for API key and token handling.
- See the Warranty and Refund Policy for uptime commitments and service credits.
