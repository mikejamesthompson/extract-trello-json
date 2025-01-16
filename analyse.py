import json
import csv


def extract_bug_cards(trello_json_path: str, output_csv_path: str):
    # Read the Trello JSON file
    with open(trello_json_path, "r", encoding="utf-8") as f:
        board_data = json.load(f)

    # Find the ID of the "severity" custom field and create severity mapping
    severity_field_id = None
    severity_options = {}
    for custom_field in board_data.get("customFields", []):
        if custom_field.get("name", "").lower() == "severity":
            severity_field_id = custom_field["id"]
            # Create mapping of severity option IDs to their text values
            for option in custom_field.get("options", []):
                severity_options[option.get("id")] = option.get("value", {}).get(
                    "text", "Unknown"
                )
            break

    # Create mapping of list IDs to names
    list_names = {
        list_data["id"]: list_data.get("name", "Unknown")
        for list_data in board_data.get("lists", [])
    }

    # Extract bug cards
    bug_cards = []
    for card in board_data.get("cards", []):
        # Skip archived cards
        if card.get("closed", False):
            continue

        # Check if card has 'bug' label
        labels = [label.get("name", "").lower() for label in card.get("labels", [])]
        if "bug" in labels:
            # Find severity value
            severity = "Not set"
            for custom_field_item in card.get("customFieldItems", []):
                if custom_field_item.get("idCustomField") == severity_field_id:
                    option_id = custom_field_item.get("idValue")
                    severity = severity_options.get(option_id, "Not set")

            bug_cards.append(
                {
                    "id": card.get("idShort", ""),
                    "name": card.get("name", ""),
                    "description": card.get("desc", ""),
                    "severity": severity,
                    "list": list_names.get(card.get("idList"), "Unknown"),
                    "url": card.get("shortUrl", ""),
                }
            )

    # Write to CSV
    with open(output_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["id", "name", "description", "severity", "list", "url"]
        )
        writer.writeheader()
        writer.writerows(bug_cards)


if __name__ == "__main__":
    extract_bug_cards("mavis-trello-board.json", "out/bugs.csv")
