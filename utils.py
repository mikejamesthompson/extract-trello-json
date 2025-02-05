from markdown_it import MarkdownIt
import os
import dotenv
import requests

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

def get_card_creator(card_id: str):
    result = make_api_request(f"board/{os.getenv('TRELLO_BOARD_ID')}/actions", {
        "filter": "createCard",
        "fields": "idMemberCreator",
        "idModels": card_id
    })

    if len(result) == 0: # Creator is no longer a member of the board
        return None

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


ALL_CUSTOM_FIELDS = get_all_custom_fields()
ALL_MEMBERS = get_all_members()


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
# def extract_archived_cards(cards: list[Card], is_archived: bool=False) -> list[Card]:
#     return [card for card in cards if card.closed == is_archived]
#

#
#
# def get_custom_field_options_map(custom_field) -> dict[str, str]:
#     data = make_api_request(url_extension=f"customFields/{custom_field.get("idCustomField")}/options")
#
#     return {option.get("_id"): option.get("value").get("text") for option in data}
#