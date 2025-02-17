import re
import emoji  # pip install emoji

import utils


def md_to_jira(md: str) -> str:
    """
    Convert Markdown to Jira wiki markup.

    Supported conversions:
      • Code blocks (``` language ... ``` -> {code} blocks)
      • Headers (#, ##, ... => h1., h2., etc.)
      • Bold (**bold text** -> *bold text*)
      • Italics (*italic text* -> _italic text_)
      • Inline code (`code` -> {{code}})
      • Blockquotes (> quote -> bq. quote)
      • Links ([text](url) -> [text|url])
      • Images (![alt](url) -> !url|alt=alt!)
      • Horizontal rules (--- -> ----)
      • Strikethrough (~~text~~ -> -text-)
      • Nested lists (both ordered and unordered) with dynamic indentation.
      • Emojis: convert colon-based emoji aliases (e.g. :white_check_mark:) to Unicode emojis.

    Raises:
      ValueError: If tables are detected in the Markdown.
    """
    # Detect tables: simple heuristic - any line that starts with a pipe.
    if re.search(r"^\s*\|.*\|", md, flags=re.MULTILINE):
        raise ValueError("Tables in Markdown are not supported.")

    text = md

    # Convert code blocks with optional language.
    def code_block_sub(match):
        lang = match.group(1)
        code = match.group(2)
        if lang:
            return "{code:" + lang + "}\n" + code + "\n{code}"
        else:
            return "{code}\n" + code + "\n{code}"

    text = re.sub(r"```(\w+)?\n(.*?)\n```", code_block_sub, text, flags=re.DOTALL)

    # Convert headers: Markdown '# Header' -> Jira 'h1. Header'
    def header_sub(match):
        hashes = match.group(1)
        header_text = match.group(2)
        level = len(hashes)
        return f"h{level}. {header_text}"

    text = re.sub(r"^(#{1,6})\s+(.*)$", header_sub, text, flags=re.MULTILINE)

    # Protect bold formatting from interfering with italic conversion.
    text = re.sub(r"\*\*(.*?)\*\*", r"__BOLD_START__\1__BOLD_END__", text)

    # Convert italics: Markdown *italic* -> Jira _italic_
    text = re.sub(r"(?<!\*)\*(?!\*)(.*?)\*(?!\*)", r"_\1_", text)

    # Restore bold formatting using Jira's asterisk notation.
    text = re.sub(r"__BOLD_START__(.*?)__BOLD_END__", r"*\1*", text)

    # Convert inline code: Markdown `code` -> Jira {{code}}
    text = re.sub(r"`(.*?)`", r"{{\1}}", text)

    # --- Handle blockquotes ---
    # Remove blockquote markers on blank lines.
    text = re.sub(r"^>\s*$", "", text, flags=re.MULTILINE)
    # Convert non-blank blockquote lines.
    text = re.sub(r"^>\s+", "bq. ", text, flags=re.MULTILINE)

    # Change image URLs to point at the local version of the image in Jira
    def replace_image(match):
        alt_text = match.group(1)
        original_url = match.group(2)
        new_url = utils.get_local_file_name(original_url)
        return f"!{new_url}|width=750!"

    text = re.sub(r"!\[([^\]]*)\]\(([^)]+?)\)", replace_image, text)


    # Convert links that are not images: Markdown text -> Jira [text|url]
    text = re.sub(r"(?<!\!)\[([^\]]+?)\]\(([^)]+?)\)", r"[\1|\2]", text)

    # Convert horizontal rules: Markdown --- -> Jira ----
    text = re.sub(r"^[-]{3,}\s*$", "----", text, flags=re.MULTILINE)

    # Convert strikethroughs: Markdown ~~text~~ -> Jira -text-
    text = re.sub(r"~~(.*?)~~", r"-\1-", text)

    # --- Nested list processing (ordered & unordered) ---
    unordered_pattern = re.compile(r"^(?P<indent>\s*)[-*]\s+(?P<content>.*)$")
    ordered_pattern = re.compile(r"^(?P<indent>\s*)(?P<num>\d+\.)\s+(?P<content>.*)$")

    def convert_list_lines(text: str) -> str:
        lines = text.splitlines()
        new_lines = []
        # The indent_stack holds the indent level (number of whitespace characters) for nesting.
        indent_stack = []

        for line in lines:
            # Check if the line is an ordered or unordered list item.
            m_ordered = ordered_pattern.match(line)
            m_unordered = unordered_pattern.match(line)
            if m_ordered or m_unordered:
                # Determine type and extract details.
                if m_ordered:
                    indent = m_ordered.group("indent")
                    content = m_ordered.group("content")
                    marker_char = "#"
                else:
                    indent = m_unordered.group("indent")
                    content = m_unordered.group("content")
                    marker_char = "*"
                curr_indent = len(indent)

                # If the stack is empty, push the current indent.
                if not indent_stack:
                    indent_stack.append(curr_indent)
                else:
                    # If current indent is greater than the top of the stack,
                    # then we've increased a level.
                    if curr_indent > indent_stack[-1]:
                        indent_stack.append(curr_indent)
                    else:
                        # Pop until we find an indent level that is less than or equal to current.
                        while indent_stack and curr_indent < indent_stack[-1]:
                            indent_stack.pop()
                        # If current indent does not match the top, push it as a new level.
                        if not indent_stack or curr_indent != indent_stack[-1]:
                            indent_stack.append(curr_indent)
                level = len(indent_stack)
                new_lines.append(f"{marker_char * level} {content}")
            else:
                # Reset stack for non-list lines.
                indent_stack = []
                new_lines.append(line)
        return "\n".join(new_lines)

    text = convert_list_lines(text)

    # This will replace occurrences like :white_check_mark: with the corresponding emoji.
    text = emoji.emojize(text, language="alias")

    # Replace tags
    def replace_tags(match):
        trello_username = match.group(1)
        trello_member_id = utils.get_member_id(trello_username)
        shortcode = utils.get_member_short_code(trello_member_id)
        return f"[~{shortcode}]"

    # This pattern matches @ followed by word characters or hyphens.
    text = re.sub(r"@([\w-]+)", replace_tags, text)

    return text


# Example usage:
if __name__ == "__main__":
    md_sample = """# Heading 1
Some **bold text** and some *italic text* along with ~~strikethrough~~ formatting.

Hello @alistairwhitehorne1.

## Heading 2
A paragraph with a [link](https://example.com) and inline code: `x = 1`. :smile:

> childs form is not coming through and she is not appearing on any cohort. Do they just have to wait a bit and maybe catch her on the next session?
>
> Manage vaccinations in schools (Mavis) – Manage vaccinations in schools

- Top-level unordered item
   - Nested unordered item
        - Third-level unordered item
* Another top-level unordered item

1. First ordered item
   1. Nested ordered item
      1. Third-level ordered item
2. Second ordered item

A normal line not in a list.

```python
def hello():
    print("Hello, world!")
```

![Alt text](https://img.shields.io/badge/alt-text-green)
"""

    print(md_to_jira(md_sample))

    print(md_to_jira(""))