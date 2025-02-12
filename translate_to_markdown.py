import re


def md_to_jira(md: str) -> str:
    """
    Convert Markdown to Jira wiki markup.

    Supported conversions:
      • Code blocks (``` language ... ```)
      • Headers (#, ##, ... -> h1., h2., etc.)
      • Bold (**bold text** -> *bold text*)
      • Italics (*italic text* -> _italic text_)
      • Inline code (`code` -> {{code}})
      • Blockquotes (> quote -> bq. quote)
      • Unordered lists (- or * -> *)
      • Ordered lists (1. item -> #)
      • Links ([text](url) -> [text|url])
      • Images (![alt](url) -> !url|alt=alt!)
      • Horizontal rules (--- -> ----)
      • Strikethrough (~~text~~ -> -text-)

    Raises:
      ValueError: If tables are detected in the Markdown.
    """
    # Detect tables: simple heuristic - any line starting with a pipe.
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

    # --- Protect bold formatting from interfering with italic conversion ---
    text = re.sub(r"\*\*(.*?)\*\*", r"__BOLD_START__\1__BOLD_END__", text)

    # Convert italics: Markdown *italic* -> Jira _italic_
    text = re.sub(r"(?<!\*)\*(?!\*)(.*?)\*(?!\*)", r"_\1_", text)

    # Restore bold formatting using Jira's asterisk notation.
    text = re.sub(r"__BOLD_START__(.*?)__BOLD_END__", r"*\1*", text)

    # Convert inline code: Markdown `code` -> Jira {{code}}
    text = re.sub(r"`(.*?)`", r"{{\1}}", text)

    # Convert blockquotes: Markdown > quote -> Jira bq. quote
    text = re.sub(r"^>\s?", "bq. ", text, flags=re.MULTILINE)

    # Convert unordered lists: Markdown "- item" or "* item" -> Jira "* item"
    text = re.sub(r"^(\s*)[-*]\s+", r"\1* ", text, flags=re.MULTILINE)

    # Convert ordered lists: Markdown "1. item" -> Jira "# item"
    text = re.sub(r"^(\s*)\d+\.\s+", r"\1# ", text, flags=re.MULTILINE)

    # Convert images: Markdown !alt -> Jira !url|alt=alt!
    text = re.sub(r"!\[([^\]]*)\]\(([^)]+?)\)", r"!\2|alt=\1!", text)

    # Convert links that are not images: Markdown text -> Jira [text|url]
    text = re.sub(r"(?<!\!)\[([^\]]+?)\]\(([^)]+?)\)", r"[\1|\2]", text)

    # Convert horizontal rules: Markdown --- -> Jira ----
    text = re.sub(r"^[-]{3,}\s*$", "----", text, flags=re.MULTILINE)

    # Convert strikethrough: Markdown ~~text~~ -> Jira -text-
    text = re.sub(r"~~(.*?)~~", r"-\1-", text)

    return text


# Example usage:
if __name__ == "__main__":
    md_sample = """# Heading 1
Some **bold text** and some *italic text* along with ~~strikethrough~~ formatting.

## Heading 2
A paragraph with a [link](https://example.com) and inline code: `x = 1`.

> A blockquote

- List item one
- List item two

1. First item
2. Second item

- Top
  - in
  - same
    - in
  - out

```python
def hello():
    print("Hello, world!")
```

![Alt text](https://img.shields.io/badge/alt-text-green)

"""
    print(md_to_jira(md_sample))