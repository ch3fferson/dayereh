import re

class MarkdownToHTML:

    @staticmethod
    def convert(text):
        if not text:
            return ""

        text = str(text).replace("\r\n", "\n").strip()

        if not text:
            return ""

        def inline(segment):
            segment = re.sub(r"&", "&amp;", segment)
            segment = re.sub(r"<", "&lt;", segment)
            segment = re.sub(r">", "&gt;", segment)

            segment = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", segment)
            segment = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", segment)
            segment = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", segment)
            segment = re.sub(r"__(.+?)__", r"<strong>\1</strong>", segment)
            segment = re.sub(r"(?<!_)_(?!_)(.+?)(?<!_)_(?!_)", r"<em>\1</em>", segment)
            segment = re.sub(r"`(.+?)`", r"<code>\1</code>", segment)
            segment = re.sub(
                r"\[(.+?)\]\((https?://[^\s)]+)\)",
                r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>',
                segment,
            )

            return segment

        lines = text.split("\n")
        html_parts = []

        paragraph_buffer = []
        list_buffer = []
        list_type = [None]

        def flush_paragraph():
            if paragraph_buffer:
                joined = "<br>".join(inline(line) for line in paragraph_buffer)
                html_parts.append(f"<p>{joined}</p>")
                paragraph_buffer.clear()

        def flush_list():
            if list_buffer:
                tag = "ol" if list_type[0] == "ordered" else "ul"
                items = "".join(f"<li>{inline(item)}</li>" for item in list_buffer)
                html_parts.append(f"<{tag}>{items}</{tag}>")
                list_buffer.clear()
            list_type[0] = None

        for raw_line in lines:
            line = raw_line.strip()

            if not line:
                flush_paragraph()
                flush_list()
                continue

            heading_match = re.match(r"^(#{1,6})\s+(.*)$", line)
            if heading_match:
                flush_paragraph()
                flush_list()
                level = min(len(heading_match.group(1)) + 2, 6)
                html_parts.append(f"<h{level}>{inline(heading_match.group(2))}</h{level}>")
                continue

            hr_match = re.match(r"^(-{3,}|\*{3,}|_{3,})$", line.replace(" ", ""))
            if hr_match:
                flush_paragraph()
                flush_list()
                html_parts.append("<hr>")
                continue

            unordered_match = re.match(r"^[-*+]\s+(.*)$", line)
            if unordered_match:
                flush_paragraph()
                if list_type[0] != "unordered":
                    flush_list()
                    list_type[0] = "unordered"
                list_buffer.append(unordered_match.group(1))
                continue

            ordered_match = re.match(r"^\d+[.)]\s+(.*)$", line)
            if ordered_match:
                flush_paragraph()
                if list_type[0] != "ordered":
                    flush_list()
                    list_type[0] = "ordered"
                list_buffer.append(ordered_match.group(1))
                continue

            blockquote_match = re.match(r"^>\s?(.*)$", line)
            if blockquote_match:
                flush_paragraph()
                flush_list()
                html_parts.append(f"<blockquote>{inline(blockquote_match.group(1))}</blockquote>")
                continue

            flush_list()
            paragraph_buffer.append(line)

        flush_paragraph()
        flush_list()

        return "".join(html_parts)