# Product Listing Methodology

## Input assumptions

The API accepts non-empty content declared as an image. The committed review fixture is synthetic. Mock mode deliberately ignores image bytes and uses fixed evidence; external mode sends the in-memory image only to the explicitly configured endpoint.

## Generated fields

- `title`: concise draft listing name.
- `description`: draft buyer-facing copy.
- `tags`: non-empty categorization terms.
- `language`: requested language label.
- `warnings`: review and uncertainty notices.
- `validation_status`: currently always `draft`.
- `provider` and `provider_trace`: routing and evidence metadata without secrets.

## Validation rules

External responses must be JSON objects with non-empty string `title` and `description` fields plus a list of non-empty string tags. Invalid output becomes a generic external failure; it is never silently presented as validated content.

## Multilingual behavior

Mock mode keeps deterministic English copy while recording the requested supported language. This tests routing and schema, not translation quality. External mode requests the selected language, but a fluent reviewer must validate wording and cultural fit.

## Routing behavior

Mock mode is the default. `MOCK_AI_MODE=true` forces mock routing even if external settings are present. External mode requires `AI_PROVIDER=external`, `MOCK_AI_MODE=false`, `ENABLE_EXTERNAL_AI=true`, `EXTERNAL_AI_ENDPOINT`, `EXTERNAL_AI_API_KEY`, and `EXTERNAL_AI_MODEL`. External failures do not fall back silently because that would obscure which evidence was produced by which execution path.

## External endpoint contract

The configurable endpoint receives a JSON request containing a model identifier, message content, an in-memory data URL for the image, deterministic generation settings, and a JSON-object response requirement. The response must expose generated message content that can be parsed into the listing schema.

This repository does not embed a vendor URL, vendor SDK, vendor model name, or vendor-specific credential variable.

## Limitations

Image models can invent materials, dimensions, quality, compatibility, or use cases. Drafts require human review against source-of-truth product data. Tags are not evidence of search demand, and generated wording does not guarantee SEO results, legal compliance, or marketplace acceptance.
