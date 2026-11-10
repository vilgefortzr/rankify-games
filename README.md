# RankifyGames

A web platform for comparing video games and picking the best of the best. Users create themed collections of games, for example *"Best Assassin's Creed Game"*, *"The Witcher Trilogy"* or *"GTA Franchise"*.

Games can be added to each collection, and, most importantly, voted on. Every user gets one vote per collection, so the community decides which entry in a series is the best.

Each game page shows a short description from the public Steam API. Searching for games to add to collections also goes through the Steam API.

---

### Related repositories

- [Frontend](https://github.com/vilgefortzr/rankify-games-frontend)

## Getting Started

### Prerequisites

- Python
- Node.js

### Backend

1. Create and activate a virtual environment:

   ```bash
   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate

   # Windows
   python -m venv venv
   venv\Scripts\activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Apply database migrations:

   ```bash
   python manage.py migrate
   ```

4. Start the development server:

   ```bash
   python manage.py runserver
   ```

   The API is available at `http://localhost:8000/api/v1/`.

### Frontend

1. Install Node dependencies:

   ```bash
   npm install
   ```

2. Start the development server:

   ```bash
   npm run dev
   ```

   The app is available at `http://localhost:5173/`.

---

## Database Schema

```text
Game            (id, steam_id, title, img_url)
Collection      (id, title, genre, description, created_at, author_id -> User | null)
CollectionGame  (id, collection_id -> Collection, game_id -> Game)   unique (collection, game)
Vote            (id, collection_game_id -> CollectionGame, author_id -> User | null)
User            Django's built-in auth user (id, username, first_name, last_name, email, password, is_staff, ...)
```

A game's vote count in a collection is the number of `Vote` rows for its `CollectionGame`.


---

## REST API

All data is exchanged as JSON. Base URL: `/api/v1`.

**Access**: Public = anyone; User = a valid access token is required; Author / Admin = the collection's author or a user with `is_staff = true`.

### Collections

| Method   | Endpoint                        | Access         | Request body                            | Success                      | Errors                  |
|----------|---------------------------------|----------------|-----------------------------------------|------------------------------|-------------------------|
| `GET`    | `/collections/` (`?search=`)    | Public         | —                                       | `200` `[Collection]`         | —                       |
| `POST`   | `/collections/`                 | User           | `{ "title", "genre", "description"? }`  | `201` `Collection`           | `400` `401`             |
| `GET`    | `/collections/{collection_id}/` | Public         | —                                       | `200` `CollectionDetail`     | `404`                   |
| `PATCH`  | `/collections/{collection_id}/` | Author / Admin | any of `title`, `genre`, `description`  | `200` `CollectionUpdate`     | `400` `401` `403` `404` |
| `DELETE` | `/collections/{collection_id}/` | Author / Admin | —                                       | `204`                        | `401` `403` `404`       |


### Collection Games

| Method   | Endpoint                                         | Access         | Request body     | Success      | Errors                              |
|----------|--------------------------------------------------|----------------|------------------|--------------|-------------------------------------|
| `POST`   | `/collections/{collection_id}/games/`            | Author / Admin | `{ "steam_id" }` | `201` `Game` | `400` `401` `403` `404` `409` `503` |
| `DELETE` | `/collections/{collection_id}/games/{steam_id}/` | Author / Admin | —                | `204`        | `401` `403` `404`                   |


### Votes

| Method   | Endpoint                                                   | Access | Request body | Success                              | Errors            |
|----------|------------------------------------------------------------|--------|--------------|--------------------------------------|-------------------|
| `POST`   | `/collections/{collection_id}/votes/{collection_game_id}/` | User   | —            | `201` `{ "game_id", "votes_count" }` | `401` `404` `409` |
| `DELETE` | `/collections/{collection_id}/votes/{collection_game_id}/` | User   | —            | `204`                                | `401` `404`       |


### Games

| Method | Endpoint                | Access | Request body | Success               | Errors            |
|--------|-------------------------|--------|--------------|-----------------------|-------------------|
| `GET`  | `/games/` (`?search=`)  | Public | —            | `200` `[Game]`        | —                 |
| `GET`  | `/games/{steam_id}/`    | Public | —            | `200` `GameDetail`    | `404`             |
| `GET`  | `/steam/games/?search=` | User   | —            | `200` `[SteamResult]` | `400` `401` `503` |


### Users

| Method | Endpoint               | Access | Request body                                                                                   | Success                          | Errors      |
|--------|------------------------|--------|------------------------------------------------------------------------------------------------|----------------------------------|-------------|
| `POST` | `/auth/register/`      | Public | `{ "username", "email", "password", "password_confirmation", "first_name"?, "last_name"? }`  | `201` `User`                     | `400`       |
| `POST` | `/auth/login/`         | Public | `{ "username", "password" }`                                                                   | `200` `{ "refresh", "access" }`  | `400` `401` |
| `POST` | `/auth/token/refresh/` | Public | `{ "refresh" }`                                                                                | `200` `{ "access" }`             | `400` `401` |
| `GET`  | `/auth/me/`            | User   | —                                                                                              | `200` `CurrentUser`              | `401`       |

**Registration rules**:

| Field                   | Rules                                                                                              |
|-------------------------|----------------------------------------------------------------------------------------------------|
| `username`              | required, max 150 characters, unique                                                               |
| `first_name`            | optional, max 150 characters                                                                       |
| `last_name`             | optional, max 150 characters                                                                       |
| `email`                 | required, valid format (`name@example.com`), max 128 characters, unique                            |
| `password`              | required, 8–128 characters; must not be too common, numeric only or too similar to username/email |
| `password_confirmation` | required, must match `password`                                                                    |

Response bodies:

```jsonc
// User (POST /auth/register/)
{ "id": 1, "username": "dimas", "first_name": "", "last_name": "", "email": "dimas@example.com" }

// CurrentUser (GET /auth/me/)
{ "id": 1, "username": "dimas", "first_name": "", "last_name": "", "email": "dimas@example.com", "is_staff": false }
```

Example of a registration error:

```json
{
  "error": {
    "status": 400,
    "code": "invalid",
    "message": "Invalid input.",
    "details": {
      "password_confirmation": ["Passwords don't match."]
    }
  }
}
```

### Error Format

```json
{
  "error": {
    "status": 404,
    "code": "game_not_found",
    "message": "Game not found on Steam.",
    "details": null
  }
}
```

For `400`, `details` holds field-level errors:

```json
{
  "error": {
    "status": 400,
    "code": "invalid",
    "message": "Invalid input.",
    "details": { "genre": ["\"Action\" is not a valid choice."] }
  }
}
```

### Status Codes

| Code  | Meaning                | When                                                         |
|-------|------------------------|--------------------------------------------------------------|
| `200` | OK                     | Successful read or update                                    |
| `201` | Created                | Collection, collection game or vote created                  |
| `204` | No Content             | Successful deletion                                          |
| `400` | Bad Request            | Invalid data, malformed JSON, missing `search` on Steam search |
| `401` | Unauthorized           | No token, invalid or expired token, wrong login credentials  |
| `403` | Forbidden              | Authenticated, but not the collection's author or an admin   |
| `404` | Not Found              | Resource does not exist, no own vote to remove, game unknown to Steam |
| `405` | Method Not Allowed     | Method not supported by the endpoint                         |
| `409` | Conflict               | Game is already in the collection, user already voted in the collection |
| `415` | Unsupported Media Type | Unsupported `Content-Type` (JSON, form and multipart are accepted) |
| `500` | Internal Server Error  | Unexpected server error (Django's default response, not the error format above) |
| `503` | Service Unavailable    | Steam API is unavailable                                     |

### Authentication

1. **Login**: `POST /auth/login/` returns two tokens:
   - `access`: short-lived (**5 minutes**), sent with every request that needs authentication;
   - `refresh`: long-lived (**1 day**), used only to get a new access token.
2. **Authenticated requests**: send the access token in the `Authorization` header:

   ```http
   GET /api/v1/auth/me/
   Authorization: Bearer <access>
   ```

3. **Refresh**: when a request returns `401` because the access token has expired, send the refresh token **in the body** to `POST /auth/token/refresh/` and repeat the request with the new access token. When the refresh token expires too, the user has to log in again.
4. **Logout**: the server keeps no session, so logout means deleting both tokens on the client.

Lifetimes are set in `SIMPLE_JWT` in `config/settings.py`.

Auth error codes:

| `code`              | Status | When                                        |
|---------------------|--------|---------------------------------------------|
| `not_authenticated` | `401`  | No `Authorization` header                   |
| `token_not_valid`   | `401`  | Token is invalid, expired or of wrong type  |
| `no_active_account` | `401`  | Wrong username or password on login         |
| `permission_denied` | `403`  | Not the collection's author or an admin     |
| `vote_exists`       | `409`  | User already voted in this collection       |

**Admins**: users with `is_staff = true` can edit and delete any collection. Create one with `python manage.py createsuperuser`.
