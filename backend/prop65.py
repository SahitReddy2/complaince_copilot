import re
import json

def is_date(line):
    return bool(re.match(r"^[A-Z][a-z]+ \d{1,2}, \d{4}$", line.strip()))

def is_cas(line):
    return bool(re.match(r"^\d{2,7}-\d{2}-\d$", line.strip()))

def is_toxicity(line):
    tox_terms = {"cancer", "developmental", "reproductive", "male", "female"}
    return line.strip().lower() in tox_terms

def is_garbage(line):
    bad_keywords = [
        "STATE OF CALIFORNIA",
        "ENVIRONMENTAL PROTECTION AGENCY",
        "OFFICE OF ENVIRONMENTAL HEALTH HAZARD ASSESSMENT",
        "chemical", "cas", "date listed", "the office"
    ]
    return any(kw.lower() in line.lower() for kw in bad_keywords)

def parse_p65_text(filepath):
    with open(filepath, "r") as f:
        lines = [line.strip() for line in f if line.strip()]

    results = []
    current = {"chemical": None, "toxicity": [], "cas": None, "date_listed": None}

    for line in lines:
        if is_garbage(line):
            continue

        elif is_toxicity(line):
            current["toxicity"].append(line.strip().lower())

        elif is_cas(line):
            current["cas"] = line.strip()

        elif is_date(line):
            current["date_listed"] = line.strip()

        else:
            # Save last if it had a chemical name
            if current["chemical"]:
                results.append(current)
                current = {"chemical": None, "toxicity": [], "cas": None, "date_listed": None}
            current["chemical"] = line.strip()

    if current["chemical"]:
        results.append(current)

    return results


if __name__ == "__main__":
    data = parse_p65_text("backend/law_docs/p65chemicalslist.txt")
    with open("extracted/p65_cleaned_full.json", "w") as out:
        json.dump(data, out, indent=2)
    print(f"✅ Parsed {len(data)} entries.")
