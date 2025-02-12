from markdown_it import MarkdownIt
import os
import dotenv
import requests
import json
from datetime import datetime
import pandas as pd
from translate_to_markdown import md_to_jira

dotenv.load_dotenv()

def get_section_content_from_markdown(markdown_text: str, header_name: str) -> str | None:
    md = MarkdownIt()
    tokens = md.parse(markdown_text)

    content_lines = []
    under_header = False
    initial_level = None
    skip_next_inline = False

    for i, token in enumerate(tokens):
        if token.type == 'heading_open':
            level = int(token.tag[1])
            header_text = tokens[i + 1].content

            if not under_header and header_name.lower() in header_text.strip().lower():
                under_header = True
                initial_level = level
                skip_next_inline = True
            elif under_header and level <= initial_level:
                break
            elif under_header:
                content_lines.append('#' * level + ' ' + header_text)
                skip_next_inline = True
        elif under_header and token.type == 'inline' and token.content:
            if skip_next_inline:
                skip_next_inline = False
            else:
                content_lines.append(token.content)

    if not under_header:
        return None

    return '\n'.join(content_lines).strip()

def make_api_request(url_extension: str, params: dict={}) -> any:
    url = f"https://api.trello.com/1/{url_extension}"
    authorised_params = params | {
        "key": os.getenv('TRELLO_API_KEY'),
        "token": os.getenv('TRELLO_TOKEN')
    }
    response = requests.get(url, params=authorised_params)
    response.raise_for_status()

    return response.json()

def get_all_cards():
    return make_api_request(f"board/{os.getenv('TRELLO_BOARD_ID')}/cards")

def get_all_members():
    return make_api_request(f"board/{os.getenv('TRELLO_BOARD_ID')}/members")

def get_member_name(member_id: str) -> str:
    for member in ALL_MEMBERS:
        if member.get('id', '') == member_id:
            return member.get('fullName', '')
    return "Not found"

def get_member_id(member_username: str) -> str:
    for member in ALL_MEMBERS:
        if member.get('username', '') == member_username:
            return member.get('id', '')
    return "Not found"

def get_member_short_code(member_id: str) -> str:
    return MEMBERS_MAPPING.get(member_id, "")

def get_card_creator(card_id: str):
    result = make_api_request(f"board/{os.getenv('TRELLO_BOARD_ID')}/actions", {
        "filter": "createCard",
        "fields": "idMemberCreator",
        "idModels": card_id
    })

    if len(result) == 0: # No creator; check if the card was created by a copy action
        result = make_api_request(f"board/{os.getenv('TRELLO_BOARD_ID')}/actions", {
            "filter": "copyCard",
            "fields": "idMemberCreator",
            "idModels": card_id
        })

    if len(result) == 0: # Creator is no longer a member of the board
        return {}

    return result[0]["memberCreator"]

def get_all_custom_fields():
    data = make_api_request(url_extension=f"boards/{os.getenv('TRELLO_BOARD_ID')}/customFields")

    return {
        field.get("id") : {
            "name": field.get("name"),
            "options": {
                option.get("id") : option.get("value").get("text")
                for option in field.get("options", [])
            }
        } for field in data
    }

def get_card_custom_fields(card_id) -> dict[str, str]:
    data = make_api_request(f"cards/{card_id}/customFieldItems")

    custom_fields = {}
    for item in data:
        options = ALL_CUSTOM_FIELDS.get(item.get("idCustomField"))

        custom_fields[options.get("name", "Not found")] = options.get("options", {}).get(item.get("idValue"), "Not found")

    return custom_fields

def get_card_checklists(card_id: str):
    return make_api_request(f"card/{card_id}/checklists")

def process_checklists(checklists):
    checklist_items = ""

    for checklist in checklists:
        sorted_items = sorted(checklist.get("checkItems", []), key=lambda i: i["pos"])

        for item in sorted_items:
            if item.get("state", "") == "complete":
                checklist_items += f"+ "
            else:
                checklist_items += f"- "

            checklist_items += item.get("name", "Not found")

            if not item.get("idMember") is None:
                checklist_items += f" @{get_member_short_code(item.get("idMember"))}"

            checklist_items += "\n"

    checklist_items = checklist_items.rstrip("\n")

    return checklist_items

def get_card_comments(card_id: str):
    return make_api_request(f"card/{card_id}/actions", {
        "filter": "commentCard"
    })

def process_comments(comments):
    formatted_comments = []

    for comment in comments:
        date = comment.get("date")
        date = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%fZ")
        date = date.replace(microsecond=0)
        date = date.isoformat()
        member_id = get_member_short_code(comment.get("idMemberCreator"))
        text = comment.get("data", {}).get("text", "Not found")
        text = md_to_jira(text)

        formatted_comments.append(f"{date};{member_id};{text}")

    return formatted_comments

def get_all_lists():
    return make_api_request(f"boards/{os.getenv('TRELLO_BOARD_ID')}/lists")

def get_list_name(list_id: str) -> str:
    for column in ALL_LISTS:
        if column.get("id", "") == list_id:
            return column.get("name", "No name")
    return "Not found"

def get_jira_list_name(list_name: str, issue_type: str) -> str:
    default = COLUMNS_MAPPING.get("default_column", {}).get(issue_type, "Not found")
    return COLUMNS_MAPPING.get(list_name, {}).get(issue_type, default)

def filter_labels(labels: list[str]) -> list[str]:
    jira_labels = []

    for label in labels:
        if label.lower() in JIRA_LABELS_LOWER:
            jira_labels.append(JIRA_LABELS[JIRA_LABELS_LOWER.index(label.lower())])

    # Replace all spaces with dashes - Jira doesn't support spaces in labels
    jira_labels = [label.replace(" ", "-") for label in jira_labels]

    return jira_labels

def get_card_attachment_urls(card_id: str):
    attachments = make_api_request(f"card/{card_id}/attachments")

    return {
        "files": [attachment.get("url") for attachment in attachments if attachment.get("isUpload")],
        "links": [attachment.get("url") for attachment in attachments if not attachment.get("isUpload")]
    }

def get_attachment_data(attachment_url: str):
    auth_header = {
        "Authorization": f"OAuth oauth_consumer_key=\"{os.getenv('TRELLO_API_KEY')}\", oauth_token=\"{os.getenv('TRELLO_TOKEN')}\""
    }
    response = requests.get(attachment_url, headers=auth_header)
    response.raise_for_status()

    return response.content

def get_local_file_name(attachment_url: str):
    return attachment_url.removeprefix("https://trello.com/1/").replace("/", "-")

def save_attachment(attachment_url: str, tqdm=None):
    local_file_name = get_local_file_name(attachment_url)
    file_location = os.path.join(os.getenv("ATTACHMENT_DIRECTORY"), local_file_name)
    local_endpoint = os.path.join(os.getenv('ATTACHMENT_SERVER_ENDPOINT'), local_file_name)

    # Ensure the attachments directory exists.
    os.makedirs(os.getenv("ATTACHMENT_DIRECTORY"), exist_ok=True)

    # If file already exists, skip download.
    if os.path.exists(file_location):
        if tqdm is not None:
            tqdm.write(f"\tAttachment already exists at {file_location}, skipping download.")
        return local_endpoint
    
    image_data = get_attachment_data(attachment_url)

    with open(file_location, "wb") as f:
        f.write(image_data)
    if tqdm is not None:
        tqdm.write(f"\tSaved attachment to {file_location}")

    return local_endpoint

def get_time_from_id(card_id: str):
    return datetime.fromtimestamp(int(card_id[0:8], 16))

def write_to_csv(cards, output_file: str="output.csv"):
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

    df.to_csv(output_file, index=False)

def add_links_to_description(jira_description: str, links: list[str]):
    if len(links) == 0:
        return jira_description

    return jira_description + "\n" + \
        "h1. Links migrated from Trello\n" + \
        "* " + "\n* ".join(links)


ALL_CUSTOM_FIELDS = get_all_custom_fields()
ALL_MEMBERS = get_all_members()
with open('members_mapping.json', 'r') as f:
    MEMBERS_MAPPING = json.load(f)
ALL_LISTS = get_all_lists()
with open('columns_mapping.json', 'r') as f:
    COLUMNS_MAPPING = json.load(f)
with open('jira_labels.json', 'r') as f:
    JIRA_LABELS = json.load(f)
    JIRA_LABELS_LOWER = [label.lower() for label in JIRA_LABELS]


# def extract_cards_since(cards: list[Card], start_date: datetime) -> list[Card]:
#     return [
#         card for card in cards
#         if card.created_date > start_date
#     ]
#
# def get_links_from_cards(cards: list[Card]) -> list[str]:
#     return [card.url for card in cards]
#
# def extract_cards_with_labels(cards: list[Card], labels: list[str], match_function=all) -> list[Card]:
#     # Returns cards whose labels match the `labels` parameter.
#     # use match_function = all or any to decide whether to and- or or-match
#
#     lower_labels = [label.lower() for label in labels]
#
#     matched_cards = []
#
#     for card in cards:
#         lower_card_labels = [label.name.lower() for label in card.labels]
#
#         if match_function([
#             match_label in lower_card_labels for match_label in lower_labels
#         ]):
#             matched_cards.append(card)
#
#     return matched_cards
#
# def extract_cards_without_labels(cards: list[Card], labels: list[str], match_function=all) -> list[Card]:
#     # Returns cards whose labels do NOT match the `labels` parameter.
#     # use match_function = all or any to decide whether to and- or or-match
#
#     return extract_cards_with_labels(cards, labels, match_function=lambda booleans: not match_function(booleans))
#
# def get_custom_field_options_map(custom_field) -> dict[str, str]:
#     data = make_api_request(url_extension=f"customFields/{custom_field.get("idCustomField")}/options")
#
#     return {option.get("_id"): option.get("value").get("text") for option in data}
#