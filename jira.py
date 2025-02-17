import argparse
import utils
from tqdm import tqdm
from translate_to_markdown import md_to_jira
import concurrent.futures
import re


def process_card(card):
    # Print progress: note that concurrent printing may interleave.
    tqdm.write(f"Processing card: MAVIS-{card.get('idShort', '')} - {card.get('name', '')}")

    summary = card.get("name", "")
    labels = [label.get("name", "").lower() for label in card.get("labels", [])]
    description = card.get("desc", "")
    workaround = utils.get_section_content_from_markdown(description, "workaround")
    workaround = md_to_jira(workaround)
    release_notes = utils.get_section_content_from_markdown(description, "release note")
    release_notes = md_to_jira(release_notes)
    description = md_to_jira(description)
    members = [utils.get_member_short_code(member_id) for member_id in card.get("idMembers", [])]
    checklists = utils.get_card_checklists(card.get("id"))
    checklist_items = utils.process_checklists(checklists)
    trello_id = f"MAVIS-{card.get("idShort", "")}"
    creator = utils.get_member_short_code(utils.get_card_creator(card.get("id")).get("id", ""))
    custom_fields = utils.get_card_custom_fields(card.get("id"))
    severity = custom_fields.get("Severity", "") # TODO this doesn't check for cards which have "valid" values for Jira
    component = custom_fields.get("Feature", "")
    comments = utils.get_card_comments(card.get("id"))
    comments = utils.process_comments(comments)
    column = utils.get_list_name(card.get("idList"))
    creation_time = utils.get_time_from_id(card.get("id"))
    jira_labels = utils.filter_labels(labels) + ["Migrated-from-Trello"]

    trello_attachments = utils.get_card_attachment_urls(card.get("id"))
    trello_files = trello_attachments.get("files")
    attachments_local_urls = [utils.save_attachment(attachment, tqdm) for attachment in trello_files]

    trello_links = trello_attachments.get("links")
    description = utils.add_links_to_description(description, trello_links)

    if "bug" in labels:
        issue_type = "Bug"
    elif "ops support" in labels:
        issue_type = "Support"
    else:
        issue_type = "Story"

    status = utils.get_jira_list_name(column, issue_type) # TODO if the status is "Done" then it needs to have the "resolution" field populated with some value (I don't know what this value should be)

    version = ""
    for label in labels:
        if re.match(r'^v\d+\.\d+\.\d+$', label): # Matches vX.X.X where X is some integer
            version = label

    return {
        "summary": summary,
        "description": description,
        "severity": severity,
        "priority": severity,
        "component": component,
        "assignee": members[0] if len(members) > 0 else "",
        "collaborators": members[1:],
        "trello_id": trello_id,
        "workaround": workaround,
        "release_notes": release_notes,
        "issue_type": issue_type,
        "labels": jira_labels,
        "reporter": creator,
        "date_created": creation_time.isoformat(),
        "status": status,
        "comments": comments,
        "attachments": attachments_local_urls,
        "fix_version": version,
        "checklist_items": checklist_items,
    }

# Parallelize processing with ThreadPoolExecutor.
def process_all_cards(trello_cards):
    jira_cards = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # executor.map preserves the order of the input list.
        for result in tqdm(executor.map(process_card, trello_cards), total=len(trello_cards)):
            jira_cards.append(result)
    return jira_cards

def create_jira_csv(output_csv_path: str):
    # Get all cards from API
    trello_cards = utils.get_all_cards()

    # Exclude archived cards
    trello_cards = [card for card in trello_cards if card.get("closed") == False]

    # Restrict cards for testing
    # trello_cards = [card for card in trello_cards if card.get("idShort", "") in [
    #     1293, # No creator (otherwise also complex), v1.5.0, emojis
    #     1851, # Good markdown
    #     1933, # Links instead of attachments
    #     1992, # In done column, ops support
    #     1995, # Archived
    #     1792, # Markdown in comments
    #     1891, # Go-live for Herts - multiple collaborators
    #     1929, # Workaround
    # ]]
    # trello_cards = trello_cards[:100]

    jira_cards = process_all_cards(trello_cards)


    # Write to CSV
    utils.write_to_csv(jira_cards, output_csv_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract bug cards from Trello board JSON export"
    )
    parser.add_argument("--output", help="Path where the output CSV should be saved", default="output.csv")

    args = parser.parse_args()
    create_jira_csv(args.output)
