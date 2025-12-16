# Feature Documentation Workflow

Every new feature should ship with a short doc living in
`docs/features/<feature-name>.md` that explains:

1. The backend modules (repositories/services/api) touched by the change.
2. The frontend surface area (React component, API client, etc.) that consumes
   the backend.
3. Any schema updates made under `web/shared/contracts/`.

Keeping this documentation close to the codebase enforces the separation
between backend and frontend while giving reviewers a checklist for future
updates.
