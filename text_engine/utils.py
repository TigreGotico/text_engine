import itertools
import re
from typing import List

try:
    from quebra_frases import word_tokenize
except ImportError:
    def word_tokenize(text: str, *args, **kwargs) -> List[str]:
        return text.split()


def load_template_file(path: str) -> List[str]:
    with open(path) as f:
        lines = flatten_list([expand_template(l) for l in f.read().split("\n")
                              if l and not l.startswith("# ")])
    return lines


def flatten_list(some_list, tuples=True) -> List:
    _flatten = lambda l: [item for sublist in l for item in sublist]
    if tuples:
        while any(isinstance(x, list) or isinstance(x, tuple)
                  for x in some_list):
            some_list = _flatten(some_list)
    else:
        while any(isinstance(x, list) for x in some_list):
            some_list = _flatten(some_list)
    return some_list


def expand_template(template: str) -> List[str]:
    def expand_optional(text):
        """Replace [optional] with two options: one with and one without."""
        return re.sub(r"\[([^\[\]]+)\]", lambda m: f"({m.group(1)}|)", text)

    def expand_alternatives(text):
        """Expand (alternative|choices) into a list of choices."""
        parts = []
        for segment in re.split(r"(\([^\(\)]+\))", text):
            if segment.startswith("(") and segment.endswith(")"):
                options = segment[1:-1].split("|")
                parts.append(options)
            else:
                parts.append([segment])
        return itertools.product(*parts)

    def fully_expand(texts):
        """Iteratively expand alternatives until all possibilities are covered."""
        result = set(texts)
        while True:
            expanded = set()
            for text in result:
                options = list(expand_alternatives(text))
                expanded.update(["".join(option).strip() for option in options])
            if expanded == result:  # No new expansions found
                break
            result = expanded
        return sorted(result)  # Return a sorted list for consistency

    # Expand optional items first
    template = expand_optional(template)

    # Fully expand all combinations of alternatives
    return fully_expand([template])
