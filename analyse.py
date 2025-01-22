import json
import csv
import argparse
from markdown_it import MarkdownIt


def get_section_content(markdown_text: str, header_name: str) -> str:
    md = MarkdownIt()
    tokens = md.parse(markdown_text)

    content = []
    under_header = False

    for i, token in enumerate(tokens):
        if token.type == 'heading_open':
            header_text = tokens[i + 1].content
            if header_text.strip().lower() == header_name.lower():
                under_header = True
                continue
            elif under_header:
                break
        elif under_header and token.type == 'inline':
            content.append(token.content)

    return '\n'.join(content[1:]).strip()


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

            # Extract workaround
            description = card.get("desc", "")
            workaround = get_section_content(description, "workaround")

            bug_cards.append(
                {
                    "id": card.get("idShort", ""),
                    "name": card.get("name", ""),
                    "description": description,
                    "workaround": workaround,
                    "severity": severity,
                    "list": list_names.get(card.get("idList"), "Unknown"),
                    "url": card.get("shortUrl", ""),
                }
            )

    # Write to CSV
    with open(output_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["id", "name", "description", "workaround", "severity", "list", "url"]
        )
        writer.writeheader()
        writer.writerows(bug_cards)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract bug cards from Trello board JSON export"
    )
    parser.add_argument("input", help="Path to the Trello board JSON file")
    parser.add_argument("output", help="Path where the output CSV should be saved")

    args = parser.parse_args()
    extract_bug_cards(args.input, args.output)
