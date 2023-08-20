from spacy.tokenizer import Tokenizer
from spacy.lang.char_classes import ALPHA, ALPHA_LOWER, ALPHA_UPPER, CONCAT_QUOTES, LIST_ELLIPSES, LIST_ICONS, HYPHENS
from spacy.util import compile_infix_regex


def tokenizer_split_on_hyphens(spacy_tokenizer, split_on_hyphens: bool = False):
    LIST_SEP = [
        r"(?<=[0-9])[+\-\*^](?=[0-9-])",
        r"(?<=[{al}{q}])\.(?=[{au}{q}])".format(al=ALPHA_LOWER, au=ALPHA_UPPER, q=CONCAT_QUOTES),
        r"(?<=[{a}]),(?=[{a}])".format(a=ALPHA),
        r"(?<=[{a}0-9])[:<>=/](?=[{a}])".format(a=ALPHA),
        r"(?<=[{a}])(?:{h})(?=[{a}])".format(a=ALPHA, h=HYPHENS),
    ]

    if not split_on_hyphens:
        temp = LIST_SEP.copy()
        temp.pop()
        temp.pop(0)
        temp += [r"(?<=[0-9])[+*^](?=[0-9-])", r"(?<=[0-9])-(?=-)"]
    else:
        temp = LIST_SEP
    infixes = (
        LIST_ELLIPSES
        + LIST_ICONS
        + temp
    )

    infix_re = compile_infix_regex(infixes)

    return Tokenizer(spacy_tokenizer.vocab, prefix_search=spacy_tokenizer.tokenizer.prefix_search,
                     suffix_search=spacy_tokenizer.tokenizer.suffix_search,
                     infix_finditer=infix_re.finditer,
                     token_match=spacy_tokenizer.tokenizer.token_match,
                     rules=spacy_tokenizer.Defaults.tokenizer_exceptions)