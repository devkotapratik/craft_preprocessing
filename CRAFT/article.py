import re
from .exceptions import MissingParserError


def remove_from_regex(article: str, annotations: list, rule: str, replacement_string: str = ""):
    """Replaces string matched by a rule with replacement_string and updates the annotations
    accordingly.
    Only checks for string that follow regex format provided in rule
    
    Input params:
    article (str): article string to remove string from
    annotations (list of dict): list of annotations with each annotations having keys:
    'start', 'end', 'spanned_text', 'id', and 'concept'
    rule (str): regex rule to specify match string
    replacement_string (str): string to replace the matched string with

    Return params:
    new_article (str): updated copy input article string with all citations removed
    new_annotations (list of dict): updated copy of annotations with start and end index of
    annotations updated
    }"""

    # If we are removing some strings, the annotation's start and end index should also be changed.
    # It is easier to update them if we start removing strings from the back.
    matches = list(re.finditer(rule, article))[::-1] # Reverse to process from the back
    new_article = article
    new_annotations = annotations[::-1].copy() # Reverse and make a copy
    for match in matches:
        span = match.span()
        new_article = new_article[:span[0]] + replacement_string + new_article[span[1]:]
        offset = span[1] - span[0] - len(replacement_string) # Offset to update index of annotations
        for idx in range(len(new_annotations)):
            annotation = new_annotations[idx].copy()
            annot_spans = annotation.get("span")
            new_annot_spans = []
            for annot_span in annot_spans:
                if annot_span[0] >= span[0]: # Subtract the offset
                    new_annot_spans.append((
                        annot_span[0] - offset,
                        annot_span[1] - offset))
                else:
                    new_annot_spans.append(annot_span)
            annotation["span"] = new_annot_spans
            new_annotations[idx] = annotation
    new_annotations = new_annotations[::-1] # Reverse of already reversed annotations
    return new_article, new_annotations



def remove_citations_from_text(article: str, annotations: list):
    """Removes citations from article and updates the annotations accordingly
    only checks for citations that follow regex format: r"\[[0-9, -]+\]"
    For e.g.
    article = survival of striatal neurons [18-20] are therefore of considerable importance
    in ensuring adaptive behavior at maturity
    annotations = { 'start': 2799,
                    'end': 2816,
                    'spanned_text': 'adaptive behavior',
                    'id': 'GO:0051867',
                    'concept': 'general adaptation syndrome, behavioral process'}
    
    After removing citations:
    article = survival of striatal neurons  are therefore of considerable importance
    in ensuring adaptive behavior at maturity.
    annotations = { 'start': 2792,
                    'end': 2809,
                    'spanned_text': 'adaptive behavior',
                    'id': 'GO:0051867',
                    'concept': 'general adaptation syndrome, behavioral process'}
    
    Input params:
    article (str): article string to remove citations from
    annotations (list of dict): list of annotations with each annotations having keys:
    'start', 'end', 'spanned_text', 'id', and 'concept'

    Return params:
    new_article (str): updated copy input article string with all citations removed
    new_annotations (list of dict): updated copy of annotations with start and end index of
    annotations updated
    }
    """
    return remove_from_regex(article, annotations, r"\[[0-9, -]+\]")
    # citations = list(re.finditer(r"\[[0-9, -]+\]", article))[::-1]
    # new_article = article
    # new_annotations = annotations[::-1].copy()
    # for citation in citations:
    #     span = citation.span()
    #     offset = span[1] - span[0]
    #     new_article = new_article[:span[0]] + new_article[span[1]:]
    #     for idx in range(len(new_annotations)):
    #         annotation = new_annotations[idx].copy()
    #         if new_annotations[idx].get("start") >= span[0]:
    #             annotation.update({
    #                 "start": annotation.get("start") - offset,
    #                 "end": annotation.get("end") - offset
    #             })
    #             new_annotations[idx] = annotation
    # new_annotations = new_annotations[::-1]
    # return new_article, new_annotations


def remove_multiple_whitespaces_from_text(article: str, annotations: list):
    """Reduces two or more consecutive whitespaces between words from article to one and
    updates the annotations accordingly.
    For e.g.
    article = survival of striatal neurons     are therefore of considerable importance
    in ensuring adaptive behavior at maturity
    There are 5 white spaces between 'neurons' and 'are'
    annotations = { 'start': 2799,
                    'end': 2816,
                    'spanned_text': 'adaptive behavior',
                    'id': 'GO:0051867',
                    'concept': 'general adaptation syndrome, behavioral process'}
    
    After removing citations:
    article = survival of striatal neurons are therefore of considerable importance
    in ensuring adaptive behavior at maturity.
    annotations = { 'start': 2792,
                    'end': 2809,
                    'spanned_text': 'adaptive behavior',
                    'id': 'GO:0051867',
                    'concept': 'general adaptation syndrome, behavioral process'}
    
    Input params:
    article (str): article string to remove citations from
    annotations (list of dict): list of annotations with each annotations having keys:
    'start', 'end', 'spanned_text', 'id', and 'concept'

    Return params:
    new_article (str): updated copy input article string with all citations removed
    new_annotations (list of dict): updated copy of annotations with start and end index of
    annotations updated
    }
    """
    return remove_from_regex(article, annotations, r"[ ]{2,}", replacement_string=" ")

class Annotation:
    def __init__(self, span, spanned_text, concept, id, disjoint=None, overlapping=None):
        self.span = span
        self.spanned_text = spanned_text
        self.concept = concept
        self.id = id
        self.disjointed = disjoint
        self.overlapping = overlapping
    
    def copy(self):
        temp = Annotation(self.span, self.spanned_text, self.concept, self.id)
        temp.disjointed, temp.overlapping = self.disjointed, self.overlapping
        return temp
    
    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                print(f"Attribute '{key}' is invalid.")
    
    def _get_info(self):
        return dict(
            span=self.span, spanned_text=self.spanned_text,
            id=self.id, concept=self.concept)

    def print_info(self):
        print(self._get_info())


class Sentence:
    def __init__(self, text: str, start_idx:int = 0, next:str = ""):
        self.original_text = text
        self.text = text
        self.span = (start_idx, start_idx + len(self.text))
        self.next = next
        self.annotations = None
        self.updated_sentences = []
    
    def _get_info(self):
        all_annots = [i._get_info() for i in self.annotations]
        info = f"Original Sentence: {self.original_text}\n" + \
            f"Sentence: {self.text}\nSpan: {self.span}" + \
            f"\nNext: {repr(self.next)}\nAnnotations: {all_annots}"
        if self.updated_sentences:
            temp_info = []
            for sent in self.updated_sentences:
                temp = sent._get_info().replace("\n", "\n\t")
                temp_info.append(temp)
            temp_info = ",\n\n\t".join(temp_info)
            info = f"{info}\nUpdated Sentences: [\n\t{temp_info}\n]"
        return info

    def print_info(self):
        print(self._get_info())

    def copy(self):
        temp = Sentence(self.text, self.span[0], self.next)
        temp.original_text = self.original_text
        temp.annotations = self.annotations.copy()
        temp.updated_sentences = [i for i in self.updated_sentences]
        return temp
    

class Article:
    """An article has the entire text, corresponding annotations as well as all sentences in 
    a list (if 'segment_sentences' is called).
    """
    def __init__(self, article: str, annotations: list):
        self.original_text = article
        self.original_annotations = annotations
        self.annotations = annotations
        self.text = None
        self.sentences = []
        self.idx = 0
        if len(self.original_annotations):
            if isinstance(self.original_annotations[0], dict):
                self.annotations = [Annotation(
                    span=i.get("span"),
                    spanned_text=i.get("spanned_text"),
                    id=i.get("id"),
                    concept=i.get("concept")
                ) for i in annotations]
            
    def _split_on_newline(self, inplace=True):
        """Separates title, headings and paragraphs by new lines"""
        temp_sentences, temp_idx = [], 0
        for match in re.finditer(r"[\n]{1,}", self.original_text):
            span = match.span() # Index where the rule matches i.e., where there is a new line
            sentence = self.original_text[temp_idx: span[0]] # Get string from previous index to
            # the span index where the rule matches
            temp_sentences.append(Sentence(sentence, start_idx=temp_idx, next=match.group()))
            temp_idx = span[1] # Update the index so that the next sentences starts from here
        if inplace:
            self.sentences = temp_sentences
            self.idx = temp_idx
        else:
            return temp_sentences

    def segment_sentences(self, parser=None, inplace=True):
        if not parser:
            raise MissingParserError
        self._split_on_newline()
        segmented_sents = []
        for sentence in self.sentences:
            doc = parser(sentence.text) # Sentence segmentation using SpaCy parser
            assert doc.has_annotation("SENT_START")
            sents = list(doc.sents)
            temp_sents = []
            for idx in range(len(sents)):
                sent = sents[idx] # Sentence after segmentation
                if idx == len(sents)-1: # If the sentence is the last
                    next = sentence.next # Next character is the same as previously set
                else: # If the sentence is not the last
                    next = sent.text_with_ws.replace(sent.text, "") # Next character is the difference
                    # between sentence with whitespace and sentence without
                text = sent.text
                start_idx = sentence.span[0] + sent.start_char # Starting index to update later
                reqd_annot = []
                for annot in self.annotations:
                    annot_spans = annot.span
                    if annot_spans[0][0] >= start_idx and annot_spans[-1][1] <= start_idx + len(text):
                        temp = Annotation(
                            span=annot_spans,
                            spanned_text=annot.spanned_text,
                            concept=annot.concept,
                            id=annot.id
                        )
                        reqd_annot.append(temp)
                        # reqd_annot.append(annot) # If there are annotations whose span lies within the span
                        # of the current sentence, append to the list of required annotations
                updated_sent = Sentence(text, start_idx, next)
                updated_sent.annotations = reqd_annot # Add annotations to the sentence
                temp_sents.append(updated_sent)
            segmented_sents.extend(temp_sents)
        if not inplace:
            return segmented_sents
        self.sentences = segmented_sents
    
    def remove_citations(self, inplace=True):
        annotations = [i._get_info() for i in self.annotations] if self.annotations else self.original_text
        text = self.text if self.text else self.original_text
        new_text, new_annotations = remove_citations_from_text(text, annotations)
        if not inplace:
            return new_text, new_annotations
        self.text = new_text
        self.annotations = [Annotation(
            span=i.get("span"),
            spanned_text=i.get("spanned_text"),
            id=i.get("id"),
            concept=i.get("concept")
        ) for i in new_annotations]
    
    def remove_multiple_whitespaces(self, inplace=True):
        annotations = [i._get_info() for i in self.annotations] if self.annotations else self.original_text
        text = self.text if self.text else self.original_text
        new_text, new_annotations = remove_multiple_whitespaces_from_text(text, annotations)
        if not inplace:
            return new_text, new_annotations
        self.text = new_text
        self.annotations = [Annotation(
            span=i.get("span"),
            spanned_text=i.get("spanned_text"),
            id=i.get("id"),
            concept=i.get("concept")
        ) for i in new_annotations]
