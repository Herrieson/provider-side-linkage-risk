# Ethics and Governance

This project studies a sensitive threat model: the model API provider itself can analyze
provider-visible Agent logs. The point is not to enable targeting real users, but to test whether
broker-side identity stripping is sufficient as a privacy control.

## Data and Identity Boundaries

- Open-SWE labels are workflow, project/repo, and GitHub owner-like labels. They are not
  enterprise customer identities.
- Open-SWE does not provide reliable real user identities. Real Open-SWE user-level
  reconstruction is reported as N/A.
- Dataset B user labels are synthetic overlays injected into real Open-SWE trace substrate.
  They are mechanism labels, not real user identities.
- Qualitative profile examples are redacted and should not expose secrets, private accounts, or
  personally identifying information.

## Responsible Artifact Handling

Artifacts should separate provider-visible request fields from evaluation-only labels:

- `attack_view.jsonl` contains provider-visible approximations.
- `ground_truth.jsonl` contains evaluation labels.
- `request_provenance.jsonl` and manifests contain source metadata.

The paper should not publish raw sensitive snippets beyond redacted examples. Tables should be
aggregated.

## Provider Governance Implications

If a provider can perform this reconstruction, technical controls should be paired with
governance controls:

- purpose limitation for inference logs;
- retention limits for raw Agent requests;
- access controls around log analytics;
- audit trails for provider-side clustering/profile analysis;
- internal policies against customer re-identification;
- broker/provider contracts that specify whether content-side profiling is prohibited;
- customer-facing transparency about what is logged and for how long.

## Compliance Framing

The work is relevant to privacy regimes such as GDPR/CCPA because it studies re-identification
risk after direct identifiers are removed. The paper should avoid making legal conclusions, but
can state that content-side linkability complicates claims that API logs are anonymous simply
because explicit account IDs are absent.

## Paper Wording

Use this wording:

> We do not attempt to identify real users. Our real-data claims are limited to workflow,
> project, and GitHub-owner-like labels; user-level experiments use controlled synthetic overlays.
> The results show that provider-side governance and retention policies are necessary
> complements to broker-side identity stripping.

Avoid this wording:

> We deanonymize real users or real companies.
