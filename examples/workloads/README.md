# M0 portable workload representations

These fixtures demonstrate that the same AIM `0.2.0-draft` operation vocabulary
can represent operations originating in two different host categories:

- `code-agent-repository.json` represents a code agent reading and editing a
  repository file;
- `ci-deployment-controller.json` represents a CI/deployment controller writing
  an external configuration object and requesting a deployment.

Each file is a collection of individually schema-valid AIM records, not a new
workload-envelope contract. The records are declarative examples only. They do
not invoke a tool, write an external resource, deploy a service, authorize an
execution, establish complete effect coverage, or prove that a real adapter
preserves these declarations.

Together the fixtures exercise text editing, tool reads, external writes and
deployment effects. Their instance, attempt, definition, input, dependency,
version and evidence fields are checked by the M0 closure tests.
