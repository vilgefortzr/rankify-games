# RankifyGames

A web platform for comparing video games and picking the best of the best. Users create themed collections of games, for example *"Best Assassin's Creed Game"*, *"The Witcher Trilogy"* or *"GTA Franchise"*.

Games can be added to each collection, and, most importantly, voted on. Every user gets one vote per collection, so the community decides which entry in a series is the best.

Each game page shows a short description from the public Steam API. Searching for games to add to collections also goes through the Steam API.

---

### Related repositories

- [Frontend](https://github.com/vilgefortzr/rankify-games-frontend)
- [Backend](https://github.com/vilgefortzr/rankify-games)

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
Collection      (id, title, genre, description, created_at, author_id -> User, TBD)
CollectionGame  (id, collection_id -> Collection, game_id -> Game)   unique (collection, game)
Vote            (id, collection_game_id -> CollectionGame, user_id -> User, TBD)
User            TBD
```

A game's vote count in a collection is the number of `Vote` rows for its `CollectionGame`.

---

## REST API

All data is exchanged as JSON. Base URL: `/api/v1`.
### Collections

| Method   | Endpoint                        | Request body                            | Success                      | Errors      |
|----------|---------------------------------|-----------------------------------------|------------------------------|-------------|
| `GET`    | `/collections/` (`?search=`)    | —                                       | `200` `[Collection]`         | —           |
| `POST`   | `/collections/`                 | `{ "title", "genre", "description"? }`  | `201` `Collection`           | `400`       |
| `GET`    | `/collections/{collection_id}/` | —                                       | `200` `CollectionDetail`     | `404`       |
| `PATCH`  | `/collections/{collection_id}/` | any of `title`, `genre`, `description`  | `200` `CollectionUpdate`     | `400` `404` |
| `DELETE` | `/collections/{collection_id}/` | —                                       | `204`                        | `404`       |


### Collection Games

| Method   | Endpoint                                         | Request body     | Success      | Errors                  |
|----------|--------------------------------------------------|------------------|--------------|-------------------------|
| `POST`   | `/collections/{collection_id}/games/`            | `{ "steam_id" }` | `201` `Game` | `400` `404` `409` `503` |
| `DELETE` | `/collections/{collection_id}/games/{steam_id}/` | —                | `204`        | `404`                   |


### Votes

| Method   | Endpoint                                                  | Request body | Success                           | Errors |
|----------|-----------------------------------------------------------|--------------|-----------------------------------|--------|
| `POST`   | `/collections/{collection_id}/votes/{collection_game_id}/` | —            | `201` `{ "game_id", "votes_count" }` | `404`  |
| `DELETE` | `/collections/{collection_id}/votes/{collection_game_id}/` | —            | `204`                                | `404`  |


### Games

| Method | Endpoint                | Request body | Success               | Errors      |
|--------|-------------------------|--------------|-----------------------|-------------|
| `GET`  | `/games/` (`?search=`)  | —            | `200` `[Game]`        | —           |
| `GET`  | `/games/{steam_id}/`    | —            | `200` `GameDetail`    | `404`       |
| `GET`  | `/steam/games/?search=` | —            | `200` `[SteamResult]` | `400` `503` |


### Users

*TBD*

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
| `404` | Not Found              | Resource does not exist, no votes to remove, game unknown to Steam |
| `405` | Method Not Allowed     | Method not supported by the endpoint                         |
| `409` | Conflict               | Game is already in the collection                            |
| `415` | Unsupported Media Type | Unsupported `Content-Type` (JSON, form and multipart are accepted) |
| `500` | Internal Server Error  | Unexpected server error (Django's default response, not the error format above) |
| `503` | Service Unavailable    | Steam API is unavailable                                     |

### Authentication

*TBD*
