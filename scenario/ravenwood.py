"""
A Death at Ravenwood Manor — complete scenario data.

SOLUTION KEY (do not reveal to player):
  Murderer:    Colonel Gerald Ashworth
  Motive:      Lord Ravenwood discovered Gerald had been embezzling from the
               Ashworth family trust (which Ravenwood managed). Ravenwood was
               planning to expose him AND change his will the following morning,
               disinheriting Lady Victoria — and therefore Gerald.
  Means:       Digitalis extract (from foxglove plants in the manor garden),
               dissolved into Ravenwood's evening brandy.
  Opportunity: Gerald excused himself from dinner at 8:40 PM, claiming a
               headache. He went directly to the study, poisoned the decanter,
               and was back in his room by 9:00 PM. Ravenwood retired to his
               study at 9:10 PM and was dead by 9:45 PM.

RED HERRINGS:
  1. James Calloway — visible motive (ruinous investment dispute) and no solid
     alibi, but innocent.
  2. Dr. Eleanor Pemberton — secret lover with access to digitalis; her medical
     bag's digitalis supply is missing (she misplaced it three days ago).
  3. Oliver Thatch — was fired by Ravenwood, returned uninvited; came only to
     retrieve a threatening letter he had written.

MOTIVE → MEANS → OPPORTUNITY CHAIN (for endgame graph evaluation):
  Gerald_embezzlement_fact → motive
  Foxglove_missing + digitalis_in_glass → means
  Sophie_saw_gerald_leaving_study + Gerald_false_alibi → opportunity
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal

# ── Node type literals ────────────────────────────────────────────────────────
EdgeType = Literal[
    "KNOWS", "FAMILY_OF", "RESENTS", "ALLIED_WITH", "LOVES",
    "OWES_DEBT_TO", "BLACKMAILS", "WITNESSED", "LOCATED_IN",
    "KNOWS_FACT", "LIES_ABOUT", "MURDERED", "EMPLOYED_BY",
]


@dataclass
class Relationship:
    target_id: str
    edge_type: EdgeType
    note: str = ""          # human-readable annotation


@dataclass
class NPC:
    id: str
    name: str
    role: str
    age: int
    public_persona: str
    private_secret: str
    alibi: str
    alibi_is_true: bool
    known_facts: list[str]          # fact IDs this NPC knows
    lies_about: list[str]           # fact IDs this NPC will actively deny/lie about
    will_share_freely: list[str]    # fact IDs shared without pressure
    shares_under_pressure: list[str]  # fact IDs shared only if cornered
    relationships: list[Relationship] = field(default_factory=list)


@dataclass
class Location:
    id: str
    name: str
    description: str
    clue_ids: list[str] = field(default_factory=list)


@dataclass
class Clue:
    id: str
    description: str
    location_id: str
    supports_fact_id: str           # which fact this clue proves
    findable_by: Literal["search", "npc", "both"] = "both"


@dataclass
class Fact:
    id: str
    statement: str
    is_solution_component: bool = False   # True if part of motive/means/opportunity


@dataclass
class Event:
    id: str
    description: str
    time: str
    participants: list[str]         # NPC ids


# ══════════════════════════════════════════════════════════════════════════════
# FACTS
# ══════════════════════════════════════════════════════════════════════════════
FACTS: list[Fact] = [
    # ── Solution facts ────────────────────────────────────────────────────────
    Fact("f_gerald_embezzled",
         "Colonel Gerald Ashworth has been embezzling funds from the Ashworth "
         "family trust, which Lord Ravenwood managed as trustee.",
         is_solution_component=True),
    Fact("f_ravenwood_discovered_gerald",
         "Lord Ravenwood discovered the embezzlement three days ago and "
         "confronted Gerald in private.",
         is_solution_component=True),
    Fact("f_will_change",
         "Lord Ravenwood had an appointment with his solicitor the following "
         "morning to disinherit Lady Victoria — and therefore Colonel Ashworth.",
         is_solution_component=True),
    Fact("f_gerald_poisoned_decanter",
         "Colonel Ashworth dissolved digitalis extract into the brandy decanter "
         "in Ravenwood's study between 8:40 PM and 9:00 PM.",
         is_solution_component=True),
    Fact("f_foxglove_missing",
         "Several foxglove plants were uprooted from the east garden bed, "
         "and digitalis extract requires foxglove as its source.",
         is_solution_component=True),
    Fact("f_digitalis_in_glass",
         "The brandy glass found beside Lord Ravenwood's body contains traces "
         "of digitalis, a cardiac glycoside that can be lethal in high doses.",
         is_solution_component=True),
    Fact("f_sophie_saw_gerald",
         "Sophie Calloway saw Colonel Ashworth leaving Lord Ravenwood's study "
         "at approximately 9:15 PM — but did not realise it was significant.",
         is_solution_component=True),
    Fact("f_gerald_false_alibi",
         "Colonel Ashworth claims he was in his bedroom with a headache from "
         "8:40 PM onwards, but this is false.",
         is_solution_component=True),

    # ── Red herring facts ─────────────────────────────────────────────────────
    Fact("f_calloway_dispute",
         "James Calloway lost a significant sum in a shipping investment that "
         "Ravenwood advised him to make. He blames Ravenwood for the loss."),
    Fact("f_calloway_argument",
         "James Calloway had a loud argument with Lord Ravenwood in the library "
         "at 4 PM on the day of the murder."),
    Fact("f_pemberton_lover",
         "Dr. Eleanor Pemberton and Lord Ravenwood had a secret romantic "
         "relationship for the past two years."),
    Fact("f_pemberton_digitalis_missing",
         "Dr. Pemberton's medical bag is missing a vial of digitalis extract "
         "that she misplaced three days ago — before the murder."),
    Fact("f_thatch_fired",
         "Lord Ravenwood dismissed Oliver Thatch from his gardening post "
         "one month ago, citing missing funds from the garden budget."),
    Fact("f_thatch_letter",
         "Oliver Thatch wrote a threatening letter to Lord Ravenwood. "
         "He returned to the manor that evening to retrieve it before "
         "Ravenwood could show it to the constable."),
    Fact("f_thatch_letter_found",
         "A crumpled letter signed 'O.T.' was found behind the fireplace "
         "in the study, reading: 'You will regret what you have done to me.'"),

    # ── Background / atmosphere facts ─────────────────────────────────────────
    Fact("f_harrington_knows_pemberton",
         "Thomas Harrington, the butler, is aware of Dr. Pemberton's "
         "relationship with Lord Ravenwood, having seen them together."),
    Fact("f_whitmore_overheard",
         "Mrs. Agnes Whitmore overheard Lord Ravenwood tell someone 'I will "
         "ruin you if you do not confess' during an argument in the study "
         "at 8:30 PM. She could not identify who Ravenwood was speaking to."),
    Fact("f_cecilia_debt",
         "Cecilia Brand, the maid, owes a gambling debt to a local money-lender "
         "connected to James Calloway."),
    Fact("f_doyle_will",
         "Father Patrick Doyle visited Ravenwood last week and was told "
         "in confidence that Ravenwood intended to change his will."),
    Fact("f_dunbar_rivalry",
         "Professor Miles Dunbar was Lord Ravenwood's academic rival. Ravenwood "
         "published a paper in 1897 using research methods Dunbar developed "
         "without crediting him."),
    Fact("f_victoria_inheritance",
         "Lady Victoria Ashworth stands to inherit the bulk of the Ravenwood "
         "estate under the current will."),
    Fact("f_gerald_ledger",
         "A ledger with altered figures, hidden under the floorboards in "
         "Colonel Ashworth's guest room, documents the embezzlement."),
]

FACTS_BY_ID: dict[str, Fact] = {f.id: f for f in FACTS}


# ══════════════════════════════════════════════════════════════════════════════
# LOCATIONS
# ══════════════════════════════════════════════════════════════════════════════
LOCATIONS: list[Location] = [
    Location("loc_entrance_hall", "Entrance Hall",
             "Grand marble-floored hall with a sweeping staircase. Portraits "
             "of Ravenwood ancestors line the walls.",
             clue_ids=[]),
    Location("loc_study", "Lord Ravenwood's Study",
             "A locked oak-panelled room. A cold fireplace, mahogany desk, "
             "and a brandy decanter on the sideboard. The body was found here.",
             clue_ids=["clue_brandy_glass", "clue_thatch_letter", "clue_overturned_chair"]),
    Location("loc_dining_room", "Dining Room",
             "Long mahogany table set for twelve. The dinner party was held here.",
             clue_ids=["clue_missing_seat"]),
    Location("loc_library", "Library",
             "Floor-to-ceiling shelves. A toxicology volume lies open on the reading table.",
             clue_ids=["clue_toxicology_book"]),
    Location("loc_east_garden", "East Garden",
             "Formal garden beds. A section of foxglove plants has been uprooted.",
             clue_ids=["clue_foxglove_missing"]),
    Location("loc_kitchen", "Kitchen",
             "Warm and busy. The cook, Mrs. Hewitt, is a reliable witness.",
             clue_ids=[]),
    Location("loc_guest_corridor", "Guest Corridor",
             "A row of guest bedrooms on the first floor.",
             clue_ids=["clue_gerald_ledger"]),
    Location("loc_conservatory", "Conservatory",
             "Glass-walled room full of tropical plants. Sophie was here reading.",
             clue_ids=["clue_sophie_vantage"]),
    Location("loc_chapel", "Chapel",
             "Small stone chapel attached to the east wing.",
             clue_ids=[]),
]

LOCATIONS_BY_ID: dict[str, Location] = {l.id: l for l in LOCATIONS}


# ══════════════════════════════════════════════════════════════════════════════
# CLUES
# ══════════════════════════════════════════════════════════════════════════════
CLUES: list[Clue] = [
    Clue("clue_brandy_glass",
         "A crystal brandy glass with a faint bitter residue. Dr. Pemberton "
         "can identify it as consistent with digitalis poisoning.",
         "loc_study", "f_digitalis_in_glass", "search"),
    Clue("clue_thatch_letter",
         "A crumpled letter signed 'O.T.' found behind the fireplace grate: "
         "'You will regret what you have done to me.'",
         "loc_study", "f_thatch_letter_found", "search"),
    Clue("clue_overturned_chair",
         "A chair is overturned near the desk — suggesting a brief struggle, "
         "or that Ravenwood staggered before collapsing.",
         "loc_study", "f_digitalis_in_glass", "search"),
    Clue("clue_missing_seat",
         "The place setting for Colonel Ashworth was removed from the table "
         "around 8:40 PM — the seat was empty for nearly twenty minutes.",
         "loc_dining_room", "f_gerald_false_alibi", "npc"),
    Clue("clue_toxicology_book",
         "A library copy of 'Poisons and Their Antidotes' (2nd ed.) lies open "
         "at the chapter on cardiac glycosides. No name in the borrowing register.",
         "loc_library", "f_gerald_poisoned_decanter", "search"),
    Clue("clue_foxglove_missing",
         "Several foxglove plants have been freshly uprooted in the east bed. "
         "Oliver Thatch will notice and mention this if asked about the garden.",
         "loc_east_garden", "f_foxglove_missing", "npc"),
    Clue("clue_gerald_ledger",
         "A cloth-bound ledger hidden under a loose floorboard in Col. Ashworth's "
         "room. Pages show systematic alterations to trust account figures.",
         "loc_guest_corridor", "f_gerald_embezzled", "search"),
    Clue("clue_sophie_vantage",
         "The conservatory window has a clear view of the corridor leading to "
         "the study. Sophie was seated here at 9:15 PM.",
         "loc_conservatory", "f_sophie_saw_gerald", "npc"),
]

CLUES_BY_ID: dict[str, Clue] = {c.id: c for c in CLUES}


# ══════════════════════════════════════════════════════════════════════════════
# EVENTS (timeline)
# ══════════════════════════════════════════════════════════════════════════════
EVENTS: list[Event] = [
    Event("evt_calloway_argument", "James Calloway argues loudly with Ravenwood in the library",
          "4:00 PM", ["calloway_james", "ravenwood_lord"]),
    Event("evt_gerald_confronted", "Ravenwood privately confronts Gerald about the embezzlement",
          "6:00 PM", ["ravenwood_lord", "ashworth_gerald"]),
    Event("evt_dinner_begins", "Dinner party begins in the dining room",
          "8:00 PM", ["harrington_thomas", "ashworth_victoria", "ashworth_gerald",
                      "pemberton_eleanor", "calloway_james", "calloway_sophie",
                      "doyle_father", "dunbar_miles", "whitmore_agnes", "brand_cecilia"]),
    Event("evt_whitmore_overhears", "Mrs. Whitmore overhears argument in the study corridor",
          "8:30 PM", ["whitmore_agnes"]),
    Event("evt_gerald_leaves_dinner", "Colonel Ashworth excuses himself from dinner, citing a headache",
          "8:40 PM", ["ashworth_gerald", "ashworth_victoria"]),
    Event("evt_gerald_in_study", "Gerald enters study and poisons the brandy decanter",
          "8:45 PM", ["ashworth_gerald"]),
    Event("evt_thatch_retrieves", "Oliver Thatch slips into the study to retrieve his letter",
          "8:50 PM", ["thatch_oliver"]),
    Event("evt_gerald_leaves_study", "Gerald exits the study; Sophie sees him from the conservatory",
          "9:00 PM", ["ashworth_gerald", "calloway_sophie"]),
    Event("evt_ravenwood_retires", "Lord Ravenwood retires to his study and pours himself a brandy",
          "9:10 PM", ["ravenwood_lord"]),
    Event("evt_ravenwood_dies", "Lord Ravenwood collapses and dies from digitalis poisoning",
          "9:45 PM", ["ravenwood_lord"]),
    Event("evt_body_discovered", "Thomas Harrington discovers the body when no answer came at the door",
          "10:15 PM", ["harrington_thomas", "ravenwood_lord"]),
]

EVENTS_BY_ID: dict[str, Event] = {e.id: e for e in EVENTS}


# ══════════════════════════════════════════════════════════════════════════════
# NPCs
# ══════════════════════════════════════════════════════════════════════════════
NPCS: list[NPC] = [
    NPC(
        id="harrington_thomas",
        name="Thomas Harrington",
        role="Butler",
        age=58,
        public_persona="Impeccably proper, loyal to the household for thirty years. "
                       "Speaks only when spoken to. Knows everything that happens "
                       "below stairs and rather more that happens above.",
        private_secret="He is aware of Dr. Pemberton's relationship with Lord Ravenwood "
                       "and has quietly covered for them both out of loyalty.",
        alibi="Serving dinner in the dining room all evening — confirmed by every dinner guest.",
        alibi_is_true=True,
        known_facts=["f_harrington_knows_pemberton", "f_pemberton_lover",
                     "f_calloway_argument", "f_thatch_fired", "f_digitalis_in_glass"],
        lies_about=[],
        will_share_freely=["f_calloway_argument", "f_thatch_fired"],
        shares_under_pressure=["f_harrington_knows_pemberton", "f_pemberton_lover"],
        relationships=[
            Relationship("ashworth_gerald", "KNOWS", "Gerald was jumpy at dinner"),
            Relationship("calloway_sophie", "KNOWS", "Sophie is a sweet girl"),
            Relationship("pemberton_eleanor", "KNOWS_FACT", "knows about the affair"),
        ],
    ),
    NPC(
        id="ashworth_victoria",
        name="Lady Victoria Ashworth",
        role="Lord Ravenwood's sister",
        age=44,
        public_persona="Charming, imperious, devoted to appearances. She and Ravenwood "
                       "had a warm public relationship, though she resented his control "
                       "over the family estate.",
        private_secret="She suspects Gerald has been mismanaging their finances but has "
                       "chosen to look away. She does not know about the murder.",
        alibi="Playing cards with Mrs. Whitmore in the sitting room from 8:30 PM onwards.",
        alibi_is_true=True,
        known_facts=["f_victoria_inheritance", "f_calloway_argument"],
        lies_about=[],
        will_share_freely=["f_victoria_inheritance", "f_calloway_argument"],
        shares_under_pressure=[],
        relationships=[
            Relationship("ashworth_gerald", "ALLIED_WITH", "husband"),
            Relationship("ashworth_gerald", "FAMILY_OF", "married"),
            Relationship("whitmore_agnes", "ALLIED_WITH", "long friendship"),
        ],
    ),
    NPC(
        id="ashworth_gerald",
        name="Colonel Gerald Ashworth",
        role="Lady Victoria's husband, retired military",
        age=51,
        public_persona="Jovial, back-slapping, military bearing. Tells war stories. "
                       "Acts as though money is no concern. Is deeply in debt.",
        private_secret="He has been embezzling from the Ashworth family trust for three "
                       "years. Ravenwood discovered this and confronted him. Gerald "
                       "poisoned the brandy to silence Ravenwood before the solicitor "
                       "appointment the next morning.",
        alibi="Claims he was in his bedroom with a headache from 8:40 PM. This is FALSE. "
              "He was in the study poisoning the decanter.",
        alibi_is_true=False,
        known_facts=["f_gerald_embezzled", "f_ravenwood_discovered_gerald",
                     "f_will_change", "f_gerald_poisoned_decanter",
                     "f_foxglove_missing", "f_gerald_false_alibi"],
        lies_about=["f_gerald_embezzled", "f_ravenwood_discovered_gerald",
                    "f_gerald_poisoned_decanter", "f_gerald_false_alibi"],
        will_share_freely=[],
        shares_under_pressure=[],
        relationships=[
            Relationship("ashworth_victoria", "FAMILY_OF", "married"),
            Relationship("ashworth_victoria", "ALLIED_WITH", "will protect her ignorance"),
            Relationship("calloway_james", "KNOWS", "business acquaintance"),
        ],
    ),
    NPC(
        id="pemberton_eleanor",
        name="Dr. Eleanor Pemberton",
        role="Family physician",
        age=38,
        public_persona="Calm, clinical, highly regarded. Has attended the Ravenwood "
                       "family for six years. Speaks precisely and observes everything.",
        private_secret="She was in a secret romantic relationship with Lord Ravenwood. "
                       "She is devastated by his death and is also alarmed that her "
                       "missing digitalis vial may implicate her.",
        alibi="Treating Mrs. Hewitt the cook's sprained wrist in the kitchen from "
              "8:15 PM. Mrs. Hewitt confirms this.",
        alibi_is_true=True,
        known_facts=["f_pemberton_lover", "f_pemberton_digitalis_missing",
                     "f_digitalis_in_glass", "f_foxglove_missing"],
        lies_about=["f_pemberton_lover"],
        will_share_freely=["f_digitalis_in_glass", "f_foxglove_missing"],
        shares_under_pressure=["f_pemberton_digitalis_missing"],
        relationships=[
            Relationship("harrington_thomas", "KNOWS", "Harrington knows about the affair"),
            Relationship("calloway_james", "KNOWS", "met at dinner parties"),
        ],
    ),
    NPC(
        id="whitmore_agnes",
        name="Mrs. Agnes Whitmore",
        role="Housekeeper",
        age=62,
        public_persona="Stout, efficient, runs a tight ship. Has an excellent memory "
                       "and an instinct for when something is wrong.",
        private_secret="She overheard the argument between Ravenwood and an unknown person "
                       "at 8:30 PM. She didn't see who it was but knows it was a man's voice.",
        alibi="Playing cards with Lady Victoria in the sitting room from 8:30 PM. "
              "Confirmed by Lady Victoria.",
        alibi_is_true=True,
        known_facts=["f_whitmore_overheard", "f_calloway_argument",
                     "f_thatch_fired", "f_cecilia_debt"],
        lies_about=[],
        will_share_freely=["f_calloway_argument", "f_thatch_fired"],
        shares_under_pressure=["f_whitmore_overheard", "f_cecilia_debt"],
        relationships=[
            Relationship("ashworth_victoria", "ALLIED_WITH", "long service together"),
            Relationship("brand_cecilia", "KNOWS", "aware of Cecilia's debts"),
            Relationship("harrington_thomas", "ALLIED_WITH", "fellow senior staff"),
        ],
    ),
    NPC(
        id="calloway_james",
        name="James Calloway",
        role="Ravenwood's former business partner",
        age=47,
        public_persona="Polished merchant, all smiles. But pressed for money and bitter "
                       "about a failed investment he blames on Ravenwood's bad advice.",
        private_secret="His debt to Ravenwood is larger than anyone knows. He came to "
                       "the dinner specifically to demand repayment. He argued fiercely "
                       "with Ravenwood at 4 PM but did NOT harm him.",
        alibi="Claims he was walking the grounds alone from 8:30 PM. No witnesses.",
        alibi_is_true=True,
        known_facts=["f_calloway_dispute", "f_calloway_argument", "f_cecilia_debt"],
        lies_about=[],
        will_share_freely=["f_calloway_argument"],
        shares_under_pressure=["f_calloway_dispute", "f_cecilia_debt"],
        relationships=[
            Relationship("calloway_sophie", "FAMILY_OF", "daughter"),
            Relationship("brand_cecilia", "BLACKMAILS", "Cecilia owes him money"),
            Relationship("ashworth_gerald", "KNOWS", "met socially"),
        ],
    ),
    NPC(
        id="calloway_sophie",
        name="Sophie Calloway",
        role="James Calloway's daughter, Ravenwood's ward",
        age=22,
        public_persona="Gentle, bookish, genuinely fond of Lord Ravenwood who sponsored "
                       "her education. She is distressed by his death and desperately "
                       "wants to help find the truth.",
        private_secret="She saw Colonel Ashworth leaving the study at 9:15 PM but did "
                       "not connect it to the murder until asked directly.",
        alibi="Reading in the conservatory from 8:30 PM. No corroborating witness, "
              "but the conservatory windows give a view of the study corridor.",
        alibi_is_true=True,
        known_facts=["f_sophie_saw_gerald", "f_calloway_dispute"],
        lies_about=[],
        will_share_freely=["f_calloway_dispute", "f_sophie_saw_gerald"],
        shares_under_pressure=[],
        relationships=[
            Relationship("calloway_james", "FAMILY_OF", "father"),
            Relationship("harrington_thomas", "KNOWS", "kind to her since childhood"),
            Relationship("ashworth_gerald", "WITNESSED", "saw him leave the study"),
        ],
    ),
    NPC(
        id="doyle_father",
        name="Father Patrick Doyle",
        role="Local parish priest, family confessor",
        age=65,
        public_persona="Gentle, unflappable. Invited as a long-standing family friend. "
                       "Listens more than he speaks.",
        private_secret="Ravenwood told him in confidence last week that he intended to "
                       "change his will. Father Doyle feels bound by the confidence "
                       "but will share it if he thinks it helps justice.",
        alibi="Praying in the chapel from 8:00 PM to 10:00 PM. Cecilia confirms she "
              "saw him there when she passed through the east corridor at 9:30 PM.",
        alibi_is_true=True,
        known_facts=["f_will_change", "f_victoria_inheritance", "f_dunbar_rivalry"],
        lies_about=[],
        will_share_freely=["f_victoria_inheritance"],
        shares_under_pressure=["f_will_change"],
        relationships=[
            Relationship("ashworth_victoria", "KNOWS", "parish connection"),
            Relationship("dunbar_miles", "KNOWS", "met at intellectual gatherings"),
        ],
    ),
    NPC(
        id="brand_cecilia",
        name="Cecilia Brand",
        role="Parlour maid",
        age=26,
        public_persona="Quiet, nervous, eager to please. Has been distracted lately.",
        private_secret="She owes money to Calloway's associate. She slipped away from "
                       "her duties for 20 minutes at 9:00 PM to meet someone in the "
                       "east corridor — actually to pay an instalment on her debt. "
                       "She saw Father Doyle in the chapel and Gerald Ashworth pass "
                       "through the corridor but didn't think anything of it.",
        alibi="Claims she was clearing dishes all evening — PARTIAL: she was absent "
              "from the dining room for about 20 minutes around 9:00 PM.",
        alibi_is_true=False,
        known_facts=["f_cecilia_debt", "f_sophie_saw_gerald", "f_gerald_false_alibi"],
        lies_about=["f_cecilia_debt"],
        will_share_freely=[],
        shares_under_pressure=["f_cecilia_debt", "f_gerald_false_alibi"],
        relationships=[
            Relationship("calloway_james", "OWES_DEBT_TO", "gambling debt"),
            Relationship("whitmore_agnes", "KNOWS", "works under her"),
            Relationship("ashworth_gerald", "WITNESSED", "saw Gerald in the corridor"),
        ],
    ),
    NPC(
        id="thatch_oliver",
        name="Oliver Thatch",
        role="Former gardener (dismissed)",
        age=41,
        public_persona="Gruff, resentful. Claims he returned only to collect tools "
                       "he left behind. Visibly nervous.",
        private_secret="He returned specifically to retrieve his threatening letter "
                       "from Ravenwood's study, fearing it would be used against him. "
                       "He slipped in during the dinner, couldn't find the letter, "
                       "and left before 9:00 PM. He did NOT harm Ravenwood.",
        alibi="Claims he left the manor at 8:30 PM. He actually left closer to 9:00 PM. "
              "No solid corroboration.",
        alibi_is_true=False,
        known_facts=["f_thatch_fired", "f_thatch_letter", "f_foxglove_missing"],
        lies_about=["f_thatch_letter"],
        will_share_freely=["f_foxglove_missing"],
        shares_under_pressure=["f_thatch_fired", "f_thatch_letter"],
        relationships=[
            Relationship("whitmore_agnes", "KNOWS", "she fired him on Ravenwood's orders"),
            Relationship("harrington_thomas", "RESENTS", "Harrington enforced his dismissal"),
        ],
    ),
    NPC(
        id="dunbar_miles",
        name="Professor Miles Dunbar",
        role="Academic, Ravenwood's former colleague",
        age=55,
        public_persona="Erudite, sardonic, enjoys provoking thought. Refers to Ravenwood "
                       "as 'an interesting host' rather than a friend.",
        private_secret="He has never forgiven Ravenwood for publishing his research "
                       "without credit in 1897. He was contacted by Ravenwood's solicitor "
                       "last week — he believes Ravenwood was about to make amends "
                       "(incorrect; it was about something else entirely). He has "
                       "a credible alibi and no means.",
        alibi="Writing correspondence in his guest room. No witness, but a stack of "
              "dated letters in his handwriting corroborate his account.",
        alibi_is_true=True,
        known_facts=["f_dunbar_rivalry", "f_calloway_argument"],
        lies_about=[],
        will_share_freely=["f_dunbar_rivalry", "f_calloway_argument"],
        shares_under_pressure=[],
        relationships=[
            Relationship("doyle_father", "KNOWS", "occasional correspondence"),
            Relationship("calloway_james", "KNOWS", "met at this dinner"),
        ],
    ),
]

NPCS_BY_ID: dict[str, NPC] = {n.id: n for n in NPCS}


# ══════════════════════════════════════════════════════════════════════════════
# SOLUTION
# ══════════════════════════════════════════════════════════════════════════════
SOLUTION = {
    "murderer_id": "ashworth_gerald",
    "murderer_name": "Colonel Gerald Ashworth",
    # The player must have learned all three of these fact IDs to win
    "required_facts": [
        "f_gerald_embezzled",          # motive
        "f_digitalis_in_glass",        # means
        "f_sophie_saw_gerald",         # opportunity (or f_gerald_false_alibi)
    ],
    "full_chain": [
        "f_gerald_embezzled",
        "f_ravenwood_discovered_gerald",
        "f_will_change",
        "f_foxglove_missing",
        "f_gerald_poisoned_decanter",
        "f_digitalis_in_glass",
        "f_sophie_saw_gerald",
        "f_gerald_false_alibi",
    ],
    "narrative": (
        "Colonel Gerald Ashworth had been stealing from the Ashworth family trust "
        "for three years. Lord Ravenwood, as trustee, discovered the irregularities "
        "and confronted Gerald that evening. Knowing that Ravenwood intended to expose "
        "him the next morning — and to disinherit Lady Victoria — Gerald saw only one "
        "way out. He slipped away from dinner at 8:40 PM, dissolved digitalis extract "
        "(gathered from the manor's own foxglove beds) into Ravenwood's brandy decanter, "
        "and returned to his room before anyone noticed. Ravenwood died alone in his "
        "study at approximately 9:45 PM. Sophie Calloway saw Gerald leaving the study "
        "corridor at 9:15 PM but did not understand what she had witnessed until the "
        "detective helped her connect the pieces."
    ),
}

# ══════════════════════════════════════════════════════════════════════════════
# DEMO SEED PATH  (for --seed 42 deterministic run)
# ══════════════════════════════════════════════════════════════════════════════
# These are the player actions that, in order, will trigger:
#   - the gossip propagation mechanic (action 3)
#   - the `why` command demo (action 5)
#   - a contradiction catch (action 7)
#   - the winning accusation (action 9)
DEMO_SCRIPT_ACTIONS = [
    "examine the brandy glass in the study",
    "ask Thomas Harrington where everyone was at 8:40 PM",
    "accuse James Calloway of the murder in front of everyone",   # triggers gossip
    "ask Sophie Calloway what she saw from the conservatory",
    "why is Sophie reluctant to talk to me",                       # triggers `why`
    "search Colonel Ashworth's guest room",
    "confront Colonel Ashworth about the ledger",                  # triggers contradiction
    "ask Father Doyle about the will",
    "accuse Colonel Gerald Ashworth",                              # winning accusation
]
