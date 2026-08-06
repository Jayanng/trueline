## Trueline verdict — {{ VERDICT }}

Computed live from DataHub lineage (training data → features → models → deployments).

```
{% for table in tables -%}
  {{ table.table }}.{{ table.column }}        {{ table.change_kind }}        author: @{{ author }}
  {% for a in table.affected -%}
  └─ {{ a.name }}        {{ a.kind }}        {{ a.reason }}        {% if a.owner %}owner: @{{ a.owner }}{% endif %}
  {% endfor -%}
  VERDICT: {{ table.severity }} — {{ table.message }}
{% endfor -%}
```

{% for p in proposals %}
- `{{ p.kind }}` → {{ p.target_urn }} — {{ p.source }} — state **{{ p.state }}**
{% endfor %}

{% if dry_run %}_This run was dry-run: nothing was written to the graph._{% else %}_Write-back committed after merge._{% endif %}

---

JSON schema (machine-readable verdict, `trueline-verdict.json`):

```json
{
  "verdict": "CRITICAL | HIGH | MEDIUM | LOW | PASS",
  "tables": [
    {
      "table": "string",
      "urn": "string",
      "severity": "string",
      "changed_columns": [{"name": "string", "kind": "DROP|ADD|TYPE_CHANGE"}],
      "affected": [{"urn": "string", "kind": "string", "owner": "string|null", "env": "string|null"}],
      "message": "string"
    }
  ],
  "proposals": [{"kind": "LINEAGE|GLOSSARY_TERM", "target_urn": "string", "detail": {}, "source": "string"}],
  "dry_run": true
}
```