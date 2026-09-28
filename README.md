# Spaceport Charter System

A booking app for the Pacific Spaceport's charter fleet. It has two screens:

- **Charter a Ship** – pick a ship and a date, see what's free, and book a time.
- **Fleet Manager** – see bookings for every ship in a date range (the next 7 days by default), grouped by ship. Click a ship to open its list.

The original brief is in [ASSIGNMENT.md](ASSIGNMENT.md).

**Stack:** React + Vite on the frontend, FastAPI + SQLAlchemy on the backend, PostgreSQL in Docker for the database, and pytest for tests.

## Architecture

There are three parts: the React app in the browser, the FastAPI backend, and PostgreSQL. The frontend only displays things and sends requests, the backend checks the rules, and the database has the final say on overlapping bookings.

```mermaid
flowchart LR
    subgraph FE["Frontend: React + Vite (localhost:5173)"]
        CP["CharterPage.jsx<br/>pick ship and date,<br/>select slots, book"]
        MP["ManagerPage.jsx<br/>bookings grouped by ship"]
        APIJS["api.js<br/>all calls to the backend"]
        TIME["time.js<br/>shows times in Central"]
        CP --> APIJS
        MP --> APIJS
        CP -.-> TIME
        MP -.-> TIME
    end

    subgraph BE["Backend: FastAPI (localhost:8000)"]
        MAIN["main.py<br/>routes and HTTP errors"]
        SCHEMAS["schemas.py<br/>checks request shape,<br/>camelCase JSON"]
        RULES["rules.py<br/>operating hours, no past bookings,<br/>30-minute slots"]
        ORM["models.py + db.py<br/>SQLAlchemy models<br/>and DB sessions"]
        MAIN --> SCHEMAS
        MAIN --> RULES
        MAIN --> ORM
    end

    subgraph PG["PostgreSQL 16 in Docker (localhost:5432)"]
        SHIPS[("ships")]
        BOOKINGS[("bookings<br/>exclusion constraint:<br/>no overlaps, 30-min refuel gap")]
    end

    APIJS -- "JSON over HTTP" --> MAIN
    ORM -- "SQL via psycopg" --> SHIPS
    ORM -- "SQL via psycopg" --> BOOKINGS
    SEED["seed.py + seed_db.py"] -. "loads starting data" .-> PG
```

### What happens when someone books

```mermaid
sequenceDiagram
    actor User
    participant UI as CharterPage (React)
    participant API as FastAPI
    participant Rules as rules.py
    participant DB as PostgreSQL

    User->>UI: Pick a ship and date
    UI->>API: GET /ships/1/availability?date=2026-09-27
    API->>DB: Load bookings near that day
    DB-->>API: Bookings
    API->>Rules: day_slots()
    Rules-->>API: 32 slots with a status each
    API-->>UI: Slots (times in UTC)
    UI-->>User: Colored grid in Central Time

    User->>UI: Select green slots, enter pilot name, click Book
    UI->>API: POST /bookings
    Note over API: Pydantic checks the request (422 if invalid)<br/>Ship must exist (404 if not)
    API->>Rules: validate_booking_times()
    Note over Rules: 422 if outside 6 AM to 10 PM Central or in the past
    API->>DB: INSERT booking
    alt No clash
        DB-->>API: Saved
        API-->>UI: 201 Created
    else Overlaps another booking or its refuel gap
        DB-->>API: Exclusion constraint violation
        API-->>UI: 409 Conflict
    end
    UI->>API: Reload availability so the grid is up to date
```

### Where each rule is checked

| Rule | Checked in | Response if broken |
|---|---|---|
| Request has the right fields, a pilot name, and times with a timezone | `schemas.py` | 422 |
| Ship exists | `main.py` | 404 |
| Ends after it starts, not in the past, within 6 AM–10 PM Central | `rules.py` | 422 |
| No overlap with another booking on the same ship, 30-minute refuel gap | Postgres exclusion constraint (`models.py`) | 409 |

### Project layout

```
├── docker-compose.yml      Postgres 16
├── seed.py                 seed data generator from the brief
├── backend/
│   ├── app/
│   │   ├── main.py         API routes
│   │   ├── schemas.py      request and response models
│   │   ├── rules.py        booking rules and slot building
│   │   ├── models.py       tables and the exclusion constraint
│   │   └── db.py           database connection
│   ├── seed_db.py          loads the seed data
│   └── tests/              rule tests and API tests
└── frontend/src/
    ├── App.jsx             navigation and routes
    ├── api.js              calls to the backend
    ├── time.js             Central Time formatting
    └── pages/              CharterPage.jsx, ManagerPage.jsx
```

## How to run it

You'll need Docker, Python 3.12+ and Node 20+.

Start the database:

```bash
docker compose up -d
```

Set up and start the backend (these are Windows paths; on Mac/Linux use `.venv/bin/python`):

```bash
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python seed_db.py
.venv\Scripts\python -m uvicorn app.main:app --reload
```

The API runs on http://localhost:8000, and http://localhost:8000/docs has a page where you can try each endpoint.

`seed_db.py` recreates the tables and loads the data from `seed.py`. You can run it again any time to reset everything.

Then, in a second terminal, start the frontend:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

To run the tests (the database needs to be running):

```bash
cd backend
.venv\Scripts\python -m pytest
```

The tests use their own `spaceport_test` database, so they won't touch your data.

## API

- `GET /ships` – list of ships
- `GET /ships/{id}/availability?date=2026-09-27` – that day's half-hour slots from 6 AM to 10 PM Central, each marked `available`, `booked`, `refueling` or `past`
- `GET /bookings?fromDate=&toDate=` – bookings sorted by ship, optionally filtered by date (`shipId` works as a filter too)
- `POST /bookings` – create a booking with `shipId`, `pilotName`, `startTime` and `endTime`

When booking, you get back `201` if it worked, `404` if the ship doesn't exist, `422` if the request breaks a rule (outside hours, in the past, no timezone, and so on) and `409` if the time clashes with another booking.

## How I used AI

I used Claude Code as a pair-programming tool during development. It helped accelerate project setup, generate initial implementations for some components, explore technical approaches, and troubleshoot issues as they came up.

I owned the overall solution and made the key implementation decisions, including selecting PostgreSQL, structuring the backend and frontend, defining the booking and availability flow, and implementing the 30-minute refueling rule. I reviewed and modified the generated code throughout development rather than using it as-is, and worked through technical issues such as PostgreSQL range constraints and timezone-aware booking logic.

I also tested the application end-to-end, validated booking conflicts and edge cases, refined the UI and user flow, and reviewed the final codebase to ensure I understood and could explain each part of the implementation. AI was useful for speeding up development and discussing alternatives, while the final design decisions, validation, and project ownership remained mine.

## What I'd do next

- Add migrations (Alembic) instead of recreating tables
- Let the fleet manager cancel or edit bookings
- Keep the refueling time in one place only
- Add pagination or a calendar view on the Fleet Manager
- Add some frontend tests for the slot selection
- Put the whole app in Docker Compose so it starts with one command
