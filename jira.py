import json
import csv
import argparse
from pytz import all_timezones
import utils


def create_jira_csv(output_csv_path: str):
    # Read the Trello JSON file
    all_original_cards = utils.get_all_cards()

    all_original_cards = [card for card in all_original_cards if card.get("name", "") in ["Go-live for Herts", "When parents both submit a consent response using the same email address, the first parent's name is overwritten with the second parent's"]]

    # Extract bug cards
    cards = []
    for card in all_original_cards:
        labels = [label.get("name", "").lower() for label in card.get("labels", [])]
        description = card.get("desc", "")
        members = card.get("idMembers", []) # Need to map these to names or shortcodes
        checklists = utils.get_card_checklists(card.get("id"))
        trello_id = card.get("idShort", "")
        creator = utils.get_card_creator(card.get("id"))
        custom_fields = utils.get_card_custom_fields(card.get("id"))
        workaround = utils.get_section_content_from_markdown(description, "workaround")
        # Card dependencies? Eg blockers
        # Attachments

        if "bug" in labels:
            issue_type = "Bugs"
        elif "ops" in labels or "ops support" in labels:
            issue_type = "Support"
        else:
            issue_type = "Stories"

        cards.append(
            {
                "name": card.get("name", ""),
                "description": description,
                "severity": custom_fields.get("severity", ""),
                # "members": members,
                "trello_id": trello_id,
                # "creator": creator,
                "workaround": workaround,
                "issue_type": issue_type,
                # "labels": labels,
                "creator": creator.get("fullName", "") if not creator is None else "",
            }
        )


    # Write to CSV
    with open(output_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f , fieldnames=cards[0].keys()
        )
        writer.writeheader()
        writer.writerows(cards)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract bug cards from Trello board JSON export"
    )
    parser.add_argument("output", help="Path where the output CSV should be saved")

    args = parser.parse_args()
    create_jira_csv(args.output)
