# HV-2 transcript (final workflow result, verbatim)

Workflow returned (verbatim, error text truncated by the tool):

```json
{"tried":[{"agentType":"hv2probe:probe-agent","ok":true,"reply":"PLUGIN-AGENT-OK"},{"agentType":"probe-agent","ok":false,"error":"agent({agentType}): agent type 'probe-agent' not found. Available agents: autoresearch-ai-plugin:autoresearch-orchestrator, backend-design:boring-tech-advisor, backend-design:component-architect, backend-design:incident-investigator, backend-design:incident-thinker, backend-design:schema-reviewer, b"}]}
```

Plugin agent works as `agentType` only with the namespaced name `hv2probe:probe-agent`. The bare `probe-agent` is not found.
