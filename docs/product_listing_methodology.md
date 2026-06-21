# Product Listing Methodology

## Input assumptions

The API accepts non-empty content declared as an image. The committed review fixture is synthetic. Mock mode deliberately ignores image bytes and uses fixed evidence; Gemini mode sends the in-memory image to the selected external provider.

## Generated fields

- `title`: concise draft listing name.
- `description`: draft buyer-facing copy.
- `tags`: non-empty categorization terms.
- `language`: requested language label.
- `warnings`: review and uncertainty notices.
- `validation_status`: currently always `draft`.
- `provider` and `provider_trace`: routing and evidence metadata without secrets.

## Validation rules

External responses must be JSON objects with non-empty string `title` and `description` fields plus a list of non-empty string tags. Invalid output becomes a generic provider failure; it is never silently presented as validated content.

## Multilingual behavior

Mock mode keeps deterministic English copy while recording the requested supported language. This tests routing and schema, not translation quality. Gemini mode requests the selected language, but a fluent reviewer must validate wording and cultural fit.

## Fallback behavior

Mock mode is the default. `MOCK_AI_MODE=true` forces mock routing even if Gemini settings or a key are present. Gemini mode requires `AI_PROVIDER=gemini`, `MOCK_AI_MODE=false`, `ENABLE_EXTERNAL_AI=true`, and `GOOGLE_API_KEY`. External failures do not fall back silently because that would obscure which evidence was produced by which provider.

## Limitations

Image models can invent materials, dimensions, quality, compatibility, or use cases. Drafts require human review against source-of-truth product data. Tags are not evidence of search demand, and generated wording does not guarantee SEO results, legal compliance, or marketplace acceptance.
