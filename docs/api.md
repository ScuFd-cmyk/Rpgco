# API (Checkpoint 1)

All routes are under `/api`. Authenticated routes need `Authorization: Bearer <token>`.
Errors: `{"detail": "..."}` with 400 invalid action, 401 no/invalid session, 403 not your character, 404 missing, 409 duplicate or stale version, 422 validation, 503 DB busy.
Interactive docs: http://localhost:8000/docs

| Method & path | Auth | Body | Returns |
|---|---|---|---|
| `GET /health` | – | | `{status}` |
| `POST /accounts` | – | `{username, passphrase}` | 201 `{account, token}` |
| `POST /sessions` | – | `{username, passphrase}` | `{account, token}` |
| `DELETE /sessions` | ✓ | | 204 |
| `GET /me` | ✓ | | `{account_id, username, selected_character_id}` |
| `GET /meta` | – | | classes & locations |
| `POST /characters` | ✓ | `{name, class_id}` | 201 character |
| `GET /characters` | ✓ | | your characters |
| `GET /characters/{id}` | owner | | character |
| `POST /characters/{id}/select` | owner | | character |
| `POST /characters/{id}/travel` | owner | `{location_id, expected_version?}` | character |
| `POST /characters/{id}/gather` | owner | | `{item_id, item_name, inventory}` |
| `GET /characters/{id}/inventory` | owner | | `[{item_id, name, quantity}]` |
| `GET /world` | ✓ | | `{state: {key: {value, version, updated_at}}, adventurers}` |
| `POST /world/actions` | owner of `character_id` | `{character_id, action:"fortify", expected_version?}` | `{key, value, version}` |
| `GET /chronicle?limit=50` | ✓ | | newest-first entries |
