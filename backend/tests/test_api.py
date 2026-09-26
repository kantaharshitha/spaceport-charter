from concurrent.futures import ThreadPoolExecutor

# A fixed date safely in the future. September is CDT, so Central is UTC-05:00.
DAY = "2030-09-16"


def at(hhmm):
    return f"{DAY}T{hhmm}:00-05:00"


def book(client, start, end, ship_id=1, pilot="Ellen Ripley"):
    return client.post(
        "/bookings",
        json={"shipId": ship_id, "pilotName": pilot, "startTime": at(start), "endTime": at(end)},
    )


def test_list_ships(client):
    assert client.get("/ships").json() == [
        {"id": 1, "name": "USS Wanderer"},
        {"id": 2, "name": "Nostromo"},
    ]


def test_create_booking(client):
    res = book(client, "10:00", "12:00")
    assert res.status_code == 201
    body = res.json()
    assert body["shipId"] == 1
    assert body["pilotName"] == "Ellen Ripley"


def test_booking_inside_refuel_buffer_is_409(client):
    book(client, "10:00", "12:00")
    assert book(client, "12:15", "13:00").status_code == 409


def test_booking_exactly_after_buffer_is_accepted(client):
    book(client, "10:00", "12:00")
    assert book(client, "12:30", "13:00").status_code == 201


def test_same_time_on_another_ship_is_fine(client):
    book(client, "10:00", "12:00", ship_id=1)
    assert book(client, "10:00", "12:00", ship_id=2).status_code == 201


def test_booking_outside_operating_hours_is_422(client):
    res = book(client, "21:00", "22:30")
    assert res.status_code == 422
    assert "operating hours" in res.json()["detail"]


def test_booking_without_timezone_is_422(client):
    res = client.post(
        "/bookings",
        json={"shipId": 1, "pilotName": "Han Solo",
              "startTime": f"{DAY}T10:00:00", "endTime": f"{DAY}T11:00:00"},
    )
    assert res.status_code == 422


def test_blank_pilot_name_is_422(client):
    assert book(client, "10:00", "11:00", pilot="   ").status_code == 422


def test_unknown_ship_is_404(client):
    assert book(client, "10:00", "11:00", ship_id=99).status_code == 404


def test_concurrent_requests_for_same_slot_only_one_wins(client):
    with ThreadPoolExecutor(max_workers=5) as pool:
        codes = sorted(pool.map(lambda _: book(client, "10:00", "11:00").status_code, range(5)))
    assert codes == [201, 409, 409, 409, 409]


def test_availability_reflects_bookings(client):
    book(client, "10:00", "12:00")
    res = client.get(f"/ships/1/availability?date={DAY}")
    assert res.status_code == 200
    body = res.json()
    assert body["slotMinutes"] == 30
    assert len(body["slots"]) == 32
    status_at = {s["start"][11:16]: s["status"] for s in body["slots"]}  # keyed by UTC HH:MM
    assert status_at["14:30"] == "refueling"  # 09:30 CDT
    assert status_at["15:00"] == "booked"     # 10:00 CDT
    assert status_at["17:00"] == "refueling"  # 12:00 CDT
    assert status_at["17:30"] == "available"  # 12:30 CDT


def test_list_bookings_filters_by_central_date(client):
    book(client, "21:00", "22:00")  # 9 PM CDT on the 16th is already the 17th in UTC
    assert len(client.get(f"/bookings?fromDate={DAY}&toDate={DAY}").json()) == 1
    assert client.get("/bookings?fromDate=2030-09-17").json() == []


def test_list_bookings_filters_by_ship(client):
    book(client, "10:00", "11:00", ship_id=1)
    book(client, "10:00", "11:00", ship_id=2)
    res = client.get("/bookings?shipId=2")
    assert [b["shipId"] for b in res.json()] == [2]
