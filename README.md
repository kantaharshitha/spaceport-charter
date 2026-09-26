# Spaceport Charter System

A booking app for the Pacific Spaceport's charter fleet. It has two screens:

- **Charter a Ship** – pick a ship and a date, see what's free, and book a time.
- **Fleet Manager** – see bookings for every ship, grouped by ship.

The original brief is in [ASSIGNMENT.md](ASSIGNMENT.md).

**Stack:** React + Vite on the frontend, FastAPI + SQLAlchemy on the backend, PostgreSQL in Docker for the database, and pytest for tests.

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

## Decisions I made

**Overlaps and the refueling gap are enforced by the database.**
I went with Postgres mainly for this. The `bookings` table has an exclusion constraint that says no two bookings for the same ship can overlap, where each booking counts as running from its start to 30 minutes after its end. That one rule covers both "no overlaps" and "30 minutes of refueling". A booking can start exactly 30 minutes after the previous one ends, but not 29.

I didn't want to check for overlaps in Python first and then insert, because two people booking at the same moment could both pass the check. With the constraint, Postgres only lets one of them through. There's a test that fires five identical requests at once and checks exactly one succeeds.

One thing I ran into: Postgres wouldn't accept `end_time + interval '30 minutes'` directly in the constraint. It said index expressions must be `IMMUTABLE`, because adding an interval to a timestamp can depend on time zone settings (think of adding "1 day" over a daylight-saving change). Adding 30 minutes is always the same length of time, so I put it in a small SQL function, `booking_block`, and marked that as `IMMUTABLE`.

**Operating hours are checked in Python.**
The hours check lives in `backend/app/rules.py`, along with the rule that you can't book in the past. I kept that file free of FastAPI and database code so the rules are easy to test on their own.

**Times are stored in UTC and shown in Central.**
The database stores exact moments (`timestamptz`). When checking hours, I work out 6 AM and 10 PM Central for that specific date with `zoneinfo`, so it stays correct when daylight saving starts or ends. The API also rejects times without a timezone, since "10:00" on its own is ambiguous. The frontend shows everything in Central Time no matter where the user is.

**The backend works out availability, as 30-minute slots.**
The brief says unavailable times should come from the backend, so the booking screen asks `/availability` for one ship and one day. The server loads only the bookings near that day and marks each half-hour slot. A slot is only "available" if booking it wouldn't break the refueling gap, so any run of green slots next to each other is a valid booking. That means the frontend doesn't need to know the rules at all. I picked 30 minutes because it matches the refueling time and all the seed data is on the hour or half hour.

**Why FastAPI and Postgres.**
The backend is just a few JSON endpoints, so Django felt like more than I needed. FastAPI's request validation and the auto-generated `/docs` page were useful. I chose Postgres over SQLite because of the exclusion constraint, and Docker keeps it to one command to start.

## Things to know

- The seed data only goes up to around May 2026. `seed.py` stops after 600 bookings per ship, so dates after that start out empty. On the Fleet Manager, pick dates in May 2026 to see the seed bookings.
- The 30-minute refueling time is written in two places: `rules.py` (for showing slots) and the `booking_block` SQL function (for enforcing it). If it changes, both need updating.
- The API will accept times like 10:10, even though the screen only books in half hours. The rules still apply, it just makes the slot grid look a bit odd.
- Tables are created straight from the models rather than with migrations.

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
