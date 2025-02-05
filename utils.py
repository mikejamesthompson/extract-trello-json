from markdown_it import MarkdownIt

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