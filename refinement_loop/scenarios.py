"""
The 10 customer scenarios from the assessment brief.

Each scenario defines:
  - id             unique slug used in logs and evaluations
  - name           human-readable label
  - customer_goal  what the customer wants (plain English, given to LLM)
  - customer_info  details the simulated customer already knows (booking refs, etc.)
  - success_criteria   what a passing conversation must achieve
  - expected_apis  which webhook endpoints should be called
"""

from dataclasses import dataclass, field


@dataclass
class Scenario:
    id: str
    name: str
    customer_goal: str
    customer_info: str
    success_criteria: list[str]
    expected_apis: list[str]


SCENARIOS: list[Scenario] = [
    Scenario(
        id="book_next_available",
        name="Book next available flight",
        customer_goal=(
            "You want to fly to Tokyo as soon as possible. "
            "You are flexible on departure time but want economy class. "
            "You have no existing bookings. Your name is James Hartley."
        ),
        customer_info="Passenger name: James Hartley. No loyalty number.",
        success_criteria=[
            "Agent correctly identifies the next available flight to Tokyo",
            "Agent confirms the departure time, price and booking reference",
            "Agent books the flight and confirms success",
        ],
        expected_apis=["GET /flights/search", "POST /bookings"],
    ),
    Scenario(
        id="cheapest_within_week",
        name="Find and book cheapest ticket within a week",
        customer_goal=(
            "You want to find the cheapest available flight to any destination "
            "within the next week. Budget is your only concern. "
            "Your name is Priya Sharma."
        ),
        customer_info="Passenger name: Priya Sharma. Open to any destination.",
        success_criteria=[
            "Agent searches across all destinations within the next 7 days",
            "Agent correctly identifies the lowest-priced available flight",
            "Agent books the flight and confirms the booking reference and price",
        ],
        expected_apis=["GET /flights/search", "POST /bookings"],
    ),
    Scenario(
        id="pet_policy",
        name="Enquire about pet policy",
        customer_goal=(
            "You are travelling with a small dog (a Cavalier King Charles Spaniel, "
            "weight 7 kg). You want to know whether it can travel in the cabin "
            "or must go in the hold, and what the fees are. "
            "You do NOT want to book anything yet."
        ),
        customer_info="Pet: dog, 7 kg. No booking needed.",
        success_criteria=[
            "Agent correctly states the cabin weight limit for pets",
            "Agent explains the hold pet policy and fees",
            "Agent clarifies carrier requirements",
            "Agent does NOT attempt to book a flight",
        ],
        expected_apis=["GET /knowledge/pet-policy"],
    ),
    Scenario(
        id="reschedule_booking",
        name="Reschedule an existing booking",
        customer_goal=(
            "Your flight to Paris (booking reference TM-4821) is on Monday "
            "and you need to move it to Wednesday. Same route, any time of day. "
            "Your name is Sarah Mitchell."
        ),
        customer_info="Booking ref: TM-4821. Route: London → Paris. Original date: Monday.",
        success_criteria=[
            "Agent retrieves the existing booking using the reference",
            "Agent finds an available Wednesday flight on the same route",
            "Agent reschedules the booking and confirms the new details",
        ],
        expected_apis=["GET /bookings/{ref}", "GET /flights/search", "PUT /bookings/{ref}"],
    ),
    Scenario(
        id="baggage_allowance",
        name="Enquire about baggage allowance",
        customer_goal=(
            "You are flying economy and want to know exactly what you can bring: "
            "cabin bag dimensions and weight, checked hold bag allowance, "
            "and what excess fees look like. You have no booking yet."
        ),
        customer_info="No booking. Economy class.",
        success_criteria=[
            "Agent provides cabin bag dimensions and weight limit",
            "Agent provides checked bag weight allowance",
            "Agent explains excess baggage fees",
        ],
        expected_apis=["GET /knowledge/baggage-policy"],
    ),
    Scenario(
        id="cancel_refund",
        name="Request cancellation and refund",
        customer_goal=(
            "You want to cancel your flight to New York (booking ref TM-3301). "
            "You booked a fully flexible fare and expect a full refund. "
            "Your name is Daniel Webb."
        ),
        customer_info="Booking ref: TM-3301. Fare type: flexible. Route: London → New York.",
        success_criteria=[
            "Agent retrieves the booking and confirms the fare type",
            "Agent explains the refund policy for flexible fares",
            "Agent cancels the booking and confirms the refund amount and timeline",
        ],
        expected_apis=["GET /bookings/{ref}", "DELETE /bookings/{ref}"],
    ),
    Scenario(
        id="seat_preference",
        name="Book with seat preference",
        customer_goal=(
            "You want to book a flight to Barcelona next Friday. "
            "You must have a window seat with extra legroom. "
            "Your name is Emma Clarke."
        ),
        customer_info="Passenger: Emma Clarke. Destination: Barcelona. Date: next Friday.",
        success_criteria=[
            "Agent finds a Barcelona flight on the correct date",
            "Agent confirms window seat with extra legroom is available",
            "Agent books the flight with the specified seat preference",
            "Agent provides the booking reference and seat assignment",
        ],
        expected_apis=["GET /flights/search", "POST /bookings"],
    ),
    Scenario(
        id="add_baggage",
        name="Add extra bag to existing booking",
        customer_goal=(
            "You have an existing booking (ref TM-6610) to Rome. "
            "You need to add one extra checked bag and also declare "
            "a folding bicycle (sports equipment). "
            "Your name is Lucas Fontaine."
        ),
        customer_info="Booking ref: TM-6610. Route: London → Rome. Items: 1 extra bag + bicycle.",
        success_criteria=[
            "Agent retrieves the booking",
            "Agent confirms the extra bag fee",
            "Agent confirms the sports equipment (bicycle) surcharge",
            "Agent adds both items and confirms the updated booking",
        ],
        expected_apis=["GET /bookings/{ref}", "PATCH /bookings/{ref}/extras"],
    ),
    Scenario(
        id="checkin_and_status",
        name="Enquire about check-in times and flight status",
        customer_goal=(
            "Your flight to Dublin departs tomorrow at 09:15 (booking ref TM-2200). "
            "You want to know when online check-in opens and closes, "
            "and whether your flight is currently on time. "
            "Your name is Aoife Murphy."
        ),
        customer_info="Booking ref: TM-2200. Route: London → Dublin. Departure: tomorrow 09:15.",
        success_criteria=[
            "Agent retrieves the booking",
            "Agent states the online check-in window correctly",
            "Agent confirms the flight status (on time / delayed / gate info)",
        ],
        expected_apis=["GET /bookings/{ref}", "GET /flights/{id}/status"],
    ),
    Scenario(
        id="special_assistance",
        name="Request special assistance for reduced mobility",
        customer_goal=(
            "Your elderly mother (75) uses a wheelchair and is travelling "
            "with you to Lisbon (booking ref TM-5540). "
            "You need to arrange full wheelchair assistance from kerb to seat "
            "and an aisle wheelchair on board. "
            "Your name is Carlos Mendes."
        ),
        customer_info="Booking ref: TM-5540. Passenger needing assistance: elderly mother, wheelchair user.",
        success_criteria=[
            "Agent retrieves the booking",
            "Agent correctly describes WCHR/WCHS/WCHC codes and which applies",
            "Agent adds the appropriate wheelchair assistance request to the booking",
            "Agent confirms the assistance details and any advance check-in requirements",
        ],
        expected_apis=["GET /bookings/{ref}", "PATCH /bookings/{ref}/assistance"],
    ),
]

SCENARIO_MAP: dict[str, Scenario] = {s.id: s for s in SCENARIOS}
