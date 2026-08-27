# Product Listing Methodology

## Input assumptions

The API accepts only non-empty JPEG, PNG, and WebP uploads. It reads in 64 KiB chunks up to `MAX_UPLOAD_SIZE_BYTES` (5 MiB by default), checks the declared media type against file signatures, verifies and fully decodes the image with Pillow, and rejects payloads above `MAX_IMAGE_PIXELS` (25 million by default). The committed review fixture is synthetic. Mock mode validates but deliberately ignores image pixels; external mode sends the validated image to the configured endpoint.

## Generated fields

- `title`: concise draft listing name.
- `description`: draft buyer-facing copy.
- `tags`: 5-8 normalized, case-insensitively deduplicated terms, each at most 50 characters.
- `language`: requested language label.
- `warnings`: review and uncertainty notices.
- `validation_status`: currently always `draft`.
- `provider` and `provider_trace`: routing and evidence metadata without secrets.

## Validation rules

External responses must be JSON objects with only `title`, `description`, and `tags`. Title is trimmed, non-empty, and at most 200 characters. Description is trimmed, non-empty, and at most 4,000 characters. Tags must be a list of 5-8 non-empty strings after whitespace normalization and case-insensitive deduplication; each tag is at most 50 characters. Unsupported shapes, extra fields, malformed JSON, excessive text, invalid tag counts, and non-string values become a generic provider failure and are never silently presented as validated content. The API response uses a Pydantic model that preserves warnings, validation status, provider, and safe provider trace telemetry.

## Multilingual behavior

Mock mode keeps deterministic English copy while recording the requested supported language. This tests routing and schema, not translation quality. External mode requests the selected language, but a fluent reviewer must validate wording and cultural fit.

## Fallback behavior

Mock mode is the default. `MOCK_AI_MODE=true` forces mock routing even if external settings or a key are present. External mode requires `AI_PROVIDER=external`, `MOCK_AI_MODE=false`, `ENABLE_EXTERNAL_AI=true`, and complete endpoint/key/model configuration. External failures do not fall back silently because that would obscure which evidence was produced by which route.

## Provider execution bounds

The optional external route uses a direct HTTP boundary with explicit connect/pool, read/write, and overall request timeouts. The overall deadline includes retries and backoff. The application retries only network/timeout failures, HTTP 408/425/429, and selected 5xx responses (500/502/503/504); default retry count is one, with bounded exponential backoff and injectable jitter. Authentication, invalid input, configuration, malformed JSON, unsupported output, and schema validation failures are not retried. A process-local CLOSED/OPEN/HALF_OPEN circuit breaker stops repeated exhausted transient failures. All provider failures reach clients as a generic message without exception text, paths, keys, headers, endpoint URLs, or raw provider bodies.

## Limitations

Image models can invent materials, dimensions, quality, compatibility, or use cases. Drafts require human review against source-of-truth product data. Tags are not evidence of search demand, and generated wording does not guarantee SEO results, legal compliance, or marketplace acceptance. Upload validation is application-level and does not replace an upstream body-size limit, authentication, rate limiting, malware scanning, or content moderation. Circuit state is process-local and is not shared across serverless instances; restarts reset it. Retries can increase latency and provider quota use, and this design is not distributed fault tolerance.
