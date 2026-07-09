# Atlas API Basics

**Product:** Atlas by TechCorp, Inc.
**API version:** v4
**Document reference:** DOC-3004
**Owner:** Developer Platform Team

## Base URL

All Atlas API requests are made against the base URL `https://api.techcorp.example/v4`. The API version is included in the URL path, so integrations built against v4 will continue to work even after a new major API version is released, until v4 is formally deprecated with 12 months of advance notice.

## Authentication

Every API request must include an API key in the `X-Atlas-Key` header. API keys are generated from workspace settings by an Admin or the Owner and are scoped to a single workspace. API keys do not expire on a fixed schedule, but can be revoked at any time from workspace settings, which immediately invalidates any tokens issued from that key.

Requests using an API key receive a short-lived authentication token valid for 24 hours, used for subsequent requests in the same session. If a request is made with an expired token, the API returns error code E-1001, described in the Troubleshooting Guide; the integration should request a new token using the API key.

## Rate limits

The Atlas API enforces a rate limit of 600 requests per minute per API key. Requests beyond this limit receive an HTTP 429 response with error code E-1077. The response includes a `Retry-After` header indicating how many seconds to wait before retrying. Integrations expecting frequent updates should use webhooks instead of polling, since webhooks are not subject to the request rate limit.

## Pagination

List endpoints, such as listing tasks on a Board, are paginated. The default page size is 50 items. Clients may request a larger page using the `page_size` query parameter, up to a maximum of 200 items per page. Responses include a `next_page_token` field; requests for subsequent pages should pass this token in the `page_token` query parameter until the field is null, indicating the last page.

## Webhooks

Webhooks let an integration receive Atlas events, such as task creation or status changes, without polling. Webhook endpoints are registered from workspace settings and must be reachable over HTTPS. Atlas expects a webhook endpoint to respond within 30 seconds; endpoints that do not respond in time receive error code E-2050 and are retried up to 3 times total, with exponential backoff starting at 5 seconds between the first retry attempts. After 3 failed attempts, the delivery is marked permanently failed.

## Common endpoints

- `GET /boards` — list Boards visible to the authenticated API key, paginated as described above.
- `GET /boards/{board_id}/tasks` — list tasks on a specific Board.
- `POST /boards/{board_id}/tasks` — create a new task on a Board.
- `PATCH /tasks/{task_id}` — update fields on an existing task.
- `POST /webhooks` — register a new webhook endpoint for the workspace.

## File attachments

Files may be attached to a task through the `POST /tasks/{task_id}/attachments` endpoint. The maximum attachment size is 25MB per file; uploads exceeding this size return error code E-2003. There is no limit on the number of attachments per task beyond overall workspace storage limits.

## Error responses

All API error responses include a JSON body with an `error_code` field matching the codes described in the Troubleshooting Guide, along with a human-readable `message` field and, where applicable, a `request_id` field useful when contacting support about a specific failed request.

## SDKs

TechCorp maintains official client libraries for the Atlas API in two languages at this time, with additional languages planned. Community-maintained clients exist for other languages but are not officially supported by TechCorp.

## Cross-references

- See the Troubleshooting Guide for the full list of error codes referenced above.
- See the Security FAQ for details on how API keys and tokens are stored and encrypted.
