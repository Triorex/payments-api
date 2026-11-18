## What changed

<!-- One or two sentences. -->

## Security checklist

- [ ] No secrets, tokens or credentials in code, config or tests
- [ ] New dependencies are needed, maintained and on the license allowlist
- [ ] User input is validated; queries are parameterised
- [ ] AuthN/AuthZ unchanged, or the change is described above
- [ ] Any new risk exception is in `.security/exceptions.yaml` with an expiry date

The `pr-security / gate` check runs every paved-road control. If it fails, open the job summary:
it names the gate and the finding. Questions: #appsec or `@Triorex/appsec`.
