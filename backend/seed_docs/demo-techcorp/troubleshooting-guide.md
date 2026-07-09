# Atlas Troubleshooting Guide

**Product:** Atlas by TechCorp, Inc.
**Applies to version:** v4.2
**Document reference:** DOC-3003
**Owner:** Support Team

## How to use this guide

This guide lists the error codes most commonly encountered in Atlas, what causes them, and how to resolve them. Error codes appear in the app as a banner and in API responses as a JSON field named "error_code." If your issue is not listed here, contact support through the channel appropriate to your plan's support tier, described at the end of this guide.

## E-1001: Authentication token expired

Atlas authentication tokens are valid for 24 hours from issuance. E-1001 appears when a request is made with an expired token, either in the web app after a long period of inactivity or in an API integration that has not refreshed its token. To resolve, log out and back in through the web app, or, for API integrations, request a new token using your API key as described in the API Basics guide. E-1001 does not indicate any data loss.

## E-1042: Sync conflict

E-1042 occurs when two people edit the same task or Board field at nearly the same time while offline or on a slow connection, creating conflicting versions once both changes reach the server. When Atlas detects a sync conflict, it opens a conflict resolution dialog showing both versions side by side, allowing the user to choose which version to keep or to merge fields manually. If a conflict is not resolved within 10 minutes, Atlas automatically applies a last-write-wins resolution based on server timestamp, and a note is added to the task's activity log describing the automatic resolution.

## E-1077: Rate limit exceeded

E-1077 corresponds to an HTTP 429 response and indicates that an API key has exceeded the Atlas API rate limit of 600 requests per minute. Integrations that receive E-1077 should back off and retry after the number of seconds specified in the "Retry-After" response header. Sustained E-1077 errors usually indicate an integration is polling too frequently rather than using Atlas webhooks, which are described in the API Basics guide as a more efficient alternative to polling.

## E-2003: File upload exceeds size limit

Atlas enforces a maximum file attachment size of 25MB per file, regardless of plan. E-2003 appears when a user attempts to upload a file larger than this limit. There is currently no plan-based exception to the 25MB limit; users needing to share larger files should link to external storage through a connected Integration instead of uploading directly to Atlas.

## E-2050: Integration webhook timeout

Atlas expects a webhook endpoint to respond within 30 seconds of receiving an event. If no response is received within that window, Atlas marks the delivery as failed with error E-2050 and retries according to the standard webhook retry policy: 3 attempts total, with exponential backoff starting at 5 seconds between the first and second attempt. If all 3 attempts fail, the webhook delivery is marked permanently failed and appears in the Integrations activity log for manual review.

## Diagnosing intermittent errors

If you experience an error code intermittently and cannot reproduce it reliably, check the Atlas status page first to rule out a service-wide incident. If the status page shows no active incident, capture the error code, the approximate time it occurred, and, for API errors, the request ID from the response headers before contacting support, as this information significantly speeds up investigation.

## Support response times by plan

Support response times are tied to your Atlas plan:

- **Standard** (Starter and Team plans): first response within 24 business hours.
- **Priority** (Business plan and above): first response within 4 hours.
- **Enterprise:** first response within 1 hour, available 24 hours a day, 7 days a week.

Business and Enterprise customers can escalate a ticket by marking it "Production impacting" in the support portal, which routes it to the on-call engineer regardless of the standard response window.

## Cross-references

- See the API Basics guide for authentication, rate limits, and webhook configuration.
- See the Product Overview for a description of plan tiers referenced in the support response times above.
