# RankifyGames

Вебплатформа, що спеціалізується на відеоіграх, а саме на їх порівнянні та визначенні найкращої з найкращих. Користувачі можуть створювати з ігор спеціальні колекції за темами, наприклад: "Best Assassin's Creed Game", "The Witcher trilogy", "GTA franchise".

У колекції відповідно буде можливість додавати ігри, і найголовніше - обирати з них найкращу. У користувачів буде можливість віддати один голос за одну гру в кожній такій категорії, і таким чином спільнота зможе обрати найкращу частину серед тієї чи іншої серії ігор. 

Також про кожну гру відображатиметься короткий опис через відкритий Steam API. Пошук та список ігор для додавання в списки також буде реалізовано через Steam API.

---

## Як запустити проєкт

### Попередні вимоги
- **Python**
- **Node.js**

---

### 1. Запуск бекенду

1. **Створіть та активуйте віртуальне середовище:**
   ```bash
   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate

   # Windows
   python -m venv venv
   venv\Scripts\activate
   ```

2. **Встановіть залежності:**
   ```bash
   pip install -r requirements-dev.txt
   ```

3. **Виконайте міграції бази даних:**
   ```bash
   python manage.py migrate
   ```

4. **Запустіть сервер розробки:**
   ```bash
   python manage.py runserver
   ```
   *Бекенд буде доступний за адресою:* `http://localhost:8000/api/v1/`

---

### 2. Запуск фронтенду

1. **Встановіть Node-залежності:**
   ```bash
   npm install
   ```

2. **Запустіть сервер розробки:**
   ```bash
   npm run dev
   ```
   *Фронтенд буде доступний за адресою:* `http://localhost:5173/`


## Схема бази даних

```text
Game (id, steam_id, title, img_url)
Collection (id, title, genre, description, created_at, author_id(ForeignKey, TBD))
CollectionGame (id, collection_id(ForeignKey), game_id(ForeignKey)) - унікальна пара (collection, game)
Vote (id, collection_game_id(ForeignKey), user_id(ForeignKey, TBD))
User (TBD)
```

Кількість голосів гри в колекції це кількість записів `Vote` для відповідного `CollectionGame`.

---

## REST API

Дані передаються у форматі JSON. Базова адреса: `/api/v1`.

### Колекції

| Метод | Адреса | Тіло запиту | Відповіді |
|---|---|---|---|
| GET | `/collections/` (`?search=`) | немає | `200` |
| POST | `/collections/` | `{ "title", "genre", "description" }` | `201`; `400` |
| GET | `/collections/{collection_id}/` | немає | `200`; `404` |
| PATCH | `/collections/{collection_id}/` | `title`, `genre`, `description` (будь-які) | `200`; `400`; `404` |
| DELETE | `/collections/{collection_id}/` | немає | `204`; `404` |

### Ігри в колекції

| Метод | Адреса | Тіло запиту | Відповіді |
|---|---|---|---|
| POST | `/collections/{collection_id}/games/` | `{ "steam_id" }` | `201`; `400`; `404`; `409`; `503` |
| DELETE | `/collections/{collection_id}/games/{steam_id}/` | немає | `204`; `404` |

### Голосування

| Метод | Адреса | Тіло запиту | Відповіді |
|---|---|---|---|
| POST | `/collections/{collection_id}/votes/{collection_game_id}` | `{ "collection_game" }` | `201`; `400`; `404` |
| DELETE | `/collections/{collection_id}/votes/{collection_game_id}` | немає | `204`; `404` |

### Ігри

| Метод | Адреса | Тіло запиту | Відповіді |
|---|---|---|---|
| GET | `/games/` (`?search=`) | немає | `200` |
| GET | `/games/{steam_id}/` | немає | `200`; `404` |
| GET | `/steam/games/?search=` | немає | `200`; `400`; `503` |

### Формат помилок

```json
{ "error": { "status": 404, "message": "Гру не знайдено у Steam." } }
```

Для `400` додається `details`:

```json
{
  "error": {
    "status": 400,
    "message": "Некоректні дані.",
    "details": { "genre": ["\"Action\" is not a valid choice."] }
  }
}
```

### Коди відповідей

| Код | Значення | Коли |
|---|---|---|
| `200` | OK | успішне читання або зміна |
| `201` | Created | створено колекцію, гру або голос |
| `204` | No Content | успішне видалення |
| `400` | Bad Request | невалідні дані, зламаний JSON, порожній `search` |
| `404` | Not Found | колекції, гри чи голосу немає; Steam не знає гри |
| `405` | Method Not Allowed | метод не підтримується адресою |
| `409` | Conflict | гра вже є в колекції |
| `415` | Unsupported Media Type | тіло запиту не в JSON |
| `500` | Internal Server Error | непередбачена помилка сервера |
| `503` | Service Unavailable | Steam API недоступний |

### Автентифікація

*TBD*
