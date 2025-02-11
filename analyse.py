import json
import csv
import argparse
from markdown_it import MarkdownIt
from datetime import datetime


def get_section_content(markdown_text: str, header_name: str) -> str:
    md = MarkdownIt()
    tokens = md.parse(markdown_text)

    content = []
    under_header = False

    for i, token in enumerate(tokens):
        if token.type == "heading_open":
            header_text = tokens[i + 1].content
            if header_name.lower() in header_text.strip().lower():
                under_header = True
                continue
            elif under_header:
                break
        elif under_header and token.type == "inline":
            content.append(token.content)

    return "\n".join(content[1:]).strip()


def extract_bug_cards(
    trello_json_path: str, output_csv_path: str, filter_labels: str = None
):
    # Read the Trello JSON file
    with open(trello_json_path, "r", encoding="utf-8") as f:
        board_data = json.load(f)

    # Convert filter_labels to a set of lowercase labels if provided
    filter_label_set = (
        set(label.strip().lower() for label in filter_labels.split(","))
        if filter_labels
        else None
    )

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

        # Get card labels
        card_labels = set(
            label.get("name", "").lower() for label in card.get("labels", [])
        )

        # Skip if filter_labels is set and card doesn't have all required labels
        if filter_label_set and not filter_label_set.issubset(card_labels):
            continue

        # Find severity value
        severity = "Not set"
        for custom_field_item in card.get("customFieldItems", []):
            if custom_field_item.get("idCustomField") == severity_field_id:
                option_id = custom_field_item.get("idValue")
                severity = severity_options.get(option_id, "Not set")

        # Extract content
        description = card.get("desc", "")
        workaround = get_section_content(description, "workaround")
        servicenow = get_section_content(description, "servicenow")

        # Parse and format the date
        created_date = card.get("dateLastActivity", "")
        if created_date:
            try:
                # Parse ISO format and convert to YYYY-MM-DD HH:MM:SS
                date_obj = datetime.fromisoformat(created_date.replace("Z", "+00:00"))
                created_date = date_obj.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass  # Keep original format if parsing fails

        bug_cards.append(
            {
                "id": card.get("idShort", ""),
                "name": card.get("name", ""),
                "description": description,
                "workaround": workaround,
                "servicenow": servicenow,
                "severity": severity,
                "list": list_names.get(card.get("idList"), "Unknown"),
                "url": card.get("shortUrl", ""),
                "created": created_date,
            }
        )

    # Write to CSV
    with open(output_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "id",
                "name",
                "description",
                "workaround",
                "servicenow",
                "severity",
                "list",
                "url",
                "created",
            ],
        )
        writer.writeheader()
        writer.writerows(bug_cards)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract bug cards from Trello board JSON export"
    )
    parser.add_argument("input", help="Path to the Trello board JSON file")
    parser.add_argument("output", help="Path where the output CSV should be saved")
    parser.add_argument(
        "--labels",
        help="Comma-separated list of labels to filter by (e.g. 'bug,critical')",
    )

    args = parser.parse_args()
    extract_bug_cards(args.input, args.output, args.labels)
