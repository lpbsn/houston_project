# API contract change

Implement the requested backend/frontend API contract change.

Required workflow:
1. inspect backend serializer/view/service tests
2. update backend implementation and API tests
3. update OpenAPI schema if needed
4. update generated frontend types if needed
5. update frontend API caller, query keys, and UI usage
6. run affected backend + frontend checks

Constraints:
- no schema drift
- no local duplicate frontend types when generated types exist
- preserve stable error shapes unless explicitly changed
- document any breaking change

Final:
- Backend changed
- Frontend changed
- Schema/types updated or not needed
- Validated
- Risks