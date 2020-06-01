import re


def escape_markdown(string: str) -> str:
    return re.sub(r'([\\_*\[\]()`])', r'\\\g<1>', string)
