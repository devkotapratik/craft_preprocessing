import re


class MissingParserError(Exception):
    """ Exception to be raised when segment_sentence() method is called before setting parser
    in Article.
    """
    def __init__(self):
        self.message = """Parser NOT set. Please set parser before calling segment_sentence().
        To set a parser, either load a parser using spacy.load(model_name) or model_name.load().
        Also assert that parser is of type: spacy.lang.en.English.
        """
        # self.message = re.sub(r"\s+", " ", self.message)
        super().__init__(self.message)
