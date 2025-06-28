#!/usr/bin/env python
"""
Create one CSV file called StredoLigaResults.csv that contains every category table.
Per-event cells show:
    - 20‥1 for places 1–20
    - 0   for 21st or worse
    - DNS / DNF / DISQ for DidNotStart / DidNotFinish / all other non-OK statuses
    - blank when the competitor was not entered in that event
"""

import glob
import os
import re
import unicodedata
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime

import pandas as pd

# ---------- CONFIG -----------------------------------------------------------
XML_DIR = "./results"                          # where the *.xml files live
POINTS = {i: 21 - i for i in range(1, 21)}     # 1st → 20, … 20th → 1
NS = {"iof": "http://www.orienteering.org/datastandard/3.0"}
RESULT_FILE_NAME = "StredoLigaResults"
# -----------------------------------------------------------------------------

# ---------- helpers ----------------------------------------------------------
def normalize_class_name(raw: str) -> str:
    """Return a canonical class name (e.g. 'A - muži')."""
    if not raw:
        return ""

    name = raw.lower().strip()
    name = re.sub(r"[\u00A0\u2013\u2014\-]+", " - ", name)   # unify dashes
    name = re.sub(r"\s+", " ", name)
    name = re.sub(r" [a-z]$", "", name)                      # chop trailing ' a'
    name = unicodedata.normalize("NFKD", name)
    name = name.replace("muzi", "muži").replace("zeny", "ženy")
    name = unicodedata.normalize("NFC", name)
    return name.capitalize()


def map_status(raw: str | None) -> str | None:
    """
    Convert raw IOF <Status> to display string.
        DidNotStart   -> 'DNS'
        DidNotFinish  -> 'DNF'
        OK / '' / None -> None  (meaning: handle by position)
        everything else -> 'DISQ'
    """
    raw_lc = (raw or "").lower()
    if raw_lc == "didnotstart":
        return "DNS"
    if raw_lc == "didnotfinish":
        return "DNF"
    if raw_lc and raw_lc != "ok":
        return "DISQ"
    return None
# -----------------------------------------------------------------------------


def parse_event(path: str) -> dict:
    """Return meta + list of result dictionaries for one XML file."""
    root = ET.parse(path).getroot()
    event_name = root.findtext(".//iof:Event/iof:Name", namespaces=NS)
    event_date = root.findtext(".//iof:Event/iof:StartTime/iof:Date", namespaces=NS)

    records = []
    for class_res in root.findall(".//iof:ClassResult", NS):
        class_name = normalize_class_name(
            class_res.findtext("./iof:Class/iof:Name", namespaces=NS)
        )

        for pr in class_res.findall("./iof:PersonResult", NS):
            person = pr.find("./iof:Person", NS)
            given = person.findtext(
                "./iof:Name/iof:Given", default="", namespaces=NS
            ).strip()
            family = person.findtext(
                "./iof:Name/iof:Family", default="", namespaces=NS
            ).strip()

            svk_id = ""
            for id_node in person.findall("./iof:Id", NS):
                if id_node.get("type") == "SVK":
                    svk_id = (id_node.text or "").strip()
                    break

            pos_text = pr.findtext("./iof:Result/iof:Position", default="", namespaces=NS)
            try:
                position = int(pos_text)
                points = POINTS.get(position, 0)
            except ValueError:
                position, points = None, 0

            records.append(
                dict(
                    class_name=class_name,
                    person_key=(given, family, svk_id),
                    position=position,
                    points=points,
                    status_raw=pr.findtext("./iof:Result/iof:Status", default="", namespaces=NS),
                )
            )

    return dict(
        name=event_name,
        date_str=event_date,
        date_obj=datetime.fromisoformat(event_date),
        records=records,
    )


def build_tables(events: list[dict]) -> None:
    """Create ONE CSV (StredoLigaResults.csv) that holds all categories."""
    cols = (
        ["Pos", "Name", "FamilyName", "ID"]
        + [f"Race {i+1}" for i in range(len(events))]
        + ["Total"]
    )

    big_chunks = []
    sep_3blank = pd.DataFrame([[""] * len(cols)] * 3, columns=cols)

    categories = sorted({r["class_name"] for e in events for r in e["records"]})

    for cat in categories:
        # --- accumulate cells + totals --------------------------------------
        cells_by_comp = defaultdict(lambda: [""] * len(events))
        totals_by_comp = defaultdict(int)

        for idx, ev in enumerate(events):
            for rec in (r for r in ev["records"] if r["class_name"] == cat):
                key = rec["person_key"]

                # decide display text for this event
                status_display = map_status(rec["status_raw"])
                if status_display is not None:
                    display = status_display          # DNS / DNF / DISQ
                elif rec["position"] is None:
                    display = ""                      # not entered
                elif rec["points"] > 0:
                    display = str(rec["points"])      # 20‥1
                else:
                    display = "0"                     # 21st+

                cells_by_comp[key][idx] = display
                if display.isdigit():
                    totals_by_comp[key] += int(display)

        # --- build list of rows ---------------------------------------------
        rows = [
            [given, family, pid, *cells, totals_by_comp[(given, family, pid)]]
            for (given, family, pid), cells in cells_by_comp.items()
        ]
        rows.sort(key=lambda x: -x[-1])                # sort by Total desc
        rows = [[rk + 1] + row for rk, row in enumerate(rows)]  # add Pos

        df_cat = pd.DataFrame(rows, columns=cols)

        # --- header rows ----------------------------------------------------
        hdr_order = [""] * 4 + [f"{i+1}. kolo" for i in range(len(events))] + [""]
        hdr_dates = [""] * 4 + [e["date_str"] for e in events] + [""]
        hdr_names = (
            ["Poradie", "Meno", "Priezvisko", "SZOS ID"]
            + [e["name"] for e in events]
            + ["Body spolu"]
        )

        df_cat = pd.concat(
            [pd.DataFrame([hdr_order, hdr_dates, hdr_names], columns=cols), df_cat],
            ignore_index=True,
        )

        # --- category title + 3-row separator -------------------------------
        title_row = [""] * 4 + [cat] + [""] * (len(cols) - 5)
        df_cat = pd.concat(
            [pd.DataFrame([title_row], columns=cols), df_cat],
            ignore_index=True,
        )
        big_chunks.extend([df_cat, sep_3blank])

    final_df = pd.concat(big_chunks[:-1], ignore_index=True)  # drop last blank
    final_df.to_csv(f"{RESULT_FILE_NAME}.csv", index=False, encoding="utf-8-sig")
    print(f"✓  StredoLigaResults.csv written ({len(categories)} categories)")


# --------------------------- main -------------------------------------------
if __name__ == "__main__":
    xml_files = sorted(glob.glob(os.path.join(XML_DIR, "*.xml")))
    if not xml_files:
        raise SystemExit("No *.xml files found!")

    events = [parse_event(p) for p in xml_files]
    events.sort(key=lambda e: e["date_obj"])  # earliest → first
    build_tables(events)
