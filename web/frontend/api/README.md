# Frontend API Clients

Generate all HTTP clients from `web/shared/contracts/openapi.yaml` to make sure
the React app never drifts from the backend contract.

Example generation command once the React toolchain is in place:

```bash
cd web/frontend
npx openapi-typescript ../shared/contracts/openapi.yaml --output api/types.ts
```

Commit generated clients/types inside this directory so they stay versioned with
the backend changes that introduced them.
