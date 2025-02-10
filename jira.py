import argparse
import utils
import pandas as pd
from tqdm import tqdm


def create_jira_csv(output_csv_path: str):
    # Read the Trello JSON file
    all_original_cards = utils.get_all_cards()

    all_original_cards = [card for card in all_original_cards if card.get("idShort", "") in [1992, 1995, 1978, 1842, 1993, 1891]]

    # Extract bug cards
    cards = []
    for card in tqdm(all_original_cards):
        tqdm.write(f"Processing card: MAVIS-{card.get("idShort", "")} - {card.get("name", "")}")

        labels = [label.get("name", "").lower() for label in card.get("labels", [])]
        description = card.get("desc", "")
        members = [utils.get_member_short_code(member_id) for member_id in card.get("idMembers", [])] # Need to map these to names or shortcodes
        checklists = utils.get_card_checklists(card.get("id"))
        trello_id = card.get("idShort", "")
        creator = utils.get_member_short_code(utils.get_card_creator(card.get("id")).get("id"))
        custom_fields = utils.get_card_custom_fields(card.get("id"))
        workaround = utils.get_section_content_from_markdown(description, "workaround")
        comments = utils.get_card_comments(card.get("id"))
        comments = utils.process_comments(comments)
        column = utils.get_list_name(card.get("idList"))
        attachments = utils.get_card_attachment_urls(card.get("id"))
        attachments_contents = [utils.get_attachment_data(attachment) for attachment in attachments]
        creation_time = utils.get_time_from_id(card.get("id"))

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
                "severity": custom_fields.get("Severity", ""),
                "assignee": members[0] if len(members) > 0 else "",
                "collaborators": members[1:],
                "trello_id": trello_id, # TODO maybe make this a link instead?
                "workaround": workaround,
                "issue_type": issue_type,
                "labels": utils.filter_labels(labels), # TODO Refactor cards in trello: waiting -> blocked, herts -> Hertfordshire
                "creator": creator,
                "creation_time": creation_time.isoformat(),
                "status": utils.get_jira_list_name(column, issue_type),
                "comments": comments,
                "attachments": attachments,
            }
        )


    ## Write to CSV
    # Create initial DataFrame
    df = pd.DataFrame(cards)

    # Find list-type columns
    list_columns = [col for col in df.columns if isinstance(df[col].iloc[0], list)]

    # Process each list column
    for col in list_columns:
        # Find max length for this column
        max_length = max(len(row) for row in df[col])
        # Expand the list column
        expanded = pd.DataFrame(df[col].tolist()).fillna('')
        expanded.columns = [col] * max_length
        # Replace original column with expanded version
        df = pd.concat([df.drop(col, axis=1), expanded], axis=1)

    df.to_csv('output.csv', index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract bug cards from Trello board JSON export"
    )
    parser.add_argument("--output", help="Path where the output CSV should be saved", default="output.csv")

    args = parser.parse_args()
    create_jira_csv(args.output)
