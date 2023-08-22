from pathlib import Path
from collections import defaultdict

import shutil
import re
import xml.etree.ElementTree as ETree

from git import Repo
from CRAFT.article import Annotation, Sentence, Article


def git_clone(git_url: str, write_dir: str, remove_hidden: bool = True):
    """ Clone Github repository from url to local directory.
    # Input params:
    git_url (str): Github url to clone from
    write_dir (str | Path): directory to clone repo to
    remove_hidden (bool): option to remove hidden files and directories
    
    # Output params:
    return_paths (list of Path): list of all files and directories cloned to write_dir
    """
    write_dir = Path(write_dir)
    # Create temporary directory
    tmp_path = Path("tmp")
    if Path(tmp_path).exists(): shutil.rmtree(tmp_path)
    data = Repo.clone_from(git_url, tmp_path) # Clone to 'tmp'
    # Get all paths, reverse them in order of depth so that path at highest depth appears ahead
    # This ensures that files are removed before directories, to avoid DirectoryNotEmpty errors
    all_paths = sorted(tmp_path.rglob("*"), key=lambda x: len(x.parts), reverse=True)
    write_dir.mkdir(exist_ok=True, parents=True)
    # Remove any cloned file if it appears in write_dir
    for path in all_paths:
        target = Path.joinpath(write_dir, *path.parts[1:])
        if target.exists():
            if target.is_file(): target.unlink()
            if target.is_dir(): shutil.rmtree(target)

    # Remove all hidden files and directories - remove path starting with '.'
    if remove_hidden:
        new_paths = []
        for i in all_paths:
            if i.stem.startswith("."):
                if i.is_file():
                    i.unlink() # Remove file if it starts with a '.'
                elif i.is_dir():
                    shutil.rmtree(i) # Remove entire directory if it start with a '.'
            else:
                # Check if any parent directory is a hidden directory
                # Reverse the order with ::-1 so that the first item is closest to root directory
                hidden = [path for path in list(i.parents) if path.stem.startswith(".")][::-1]
                if len(hidden):
                    if hidden[0].exists(): # Check if hidden directory is removed in previous iterations
                        shutil.rmtree(hidden[0]) # Remove hidden directory
                else:
                    new_paths.append(i)
    else:
        new_paths = all_paths

    return_paths = []
    ### Move all files from 'tmp' to write_dir
    for path in new_paths:
        # Create new target - replace 'tmp' with write_dir
        target = Path.joinpath(write_dir, *path.parts[1:])
        # Create directories and parent of directory if required
        if path.is_dir():
            target.mkdir(exist_ok=True, parents=True)
        elif path.is_file():
            target.parent.mkdir(exist_ok=True, parents=True)
            # Move file from 'tmp' to write_dir
            path.rename(target)
        return_paths.append(target)
    # Remove 'tmp' directory
    shutil.rmtree("tmp")
    return return_paths


def get_article_by_id(source_id: str, data_dir: str | Path):
    """Returns a tuple of article and annotations given a source_id as input
    Input params:
    source_id (str): 8 digit number as source
    data_dir (str | Path): directory to search for files by source_id

    Return params:
    article (str): 'utf-8' encoded string
    annotations (dict): list of annotations with start index, end index, spanned text
    GO ID and GO concept.
    """
    reqd_files = [i for i in Path(data_dir).rglob("*") if re.search(f"{source_id}.*(.txt|.xml)?", i.stem)]
    article = [i for i in reqd_files if i.suffix == ".txt"][0].read_text("utf-8")
    annotations = defaultdict(dict)
    for xml_file in reqd_files:
        if xml_file.suffix == ".xml" and "extension" not in str(xml_file):
            root = ETree.parse(xml_file).getroot()
            assert root.attrib.get("textSource") == source_id + ".txt"
            for child in root:
                if child.tag == "annotation":
                    span_children = child.findall("span")
                    spans = defaultdict(list)
                    for span_child in span_children:
                        span = span_child.attrib
                        spans["span"].append((int(span["start"]), int(span["end"])))
                        spans["spanned_text"] = child.find("spannedText").text
                    annotations[
                        child.find("mention").attrib.get("id")].update(spans)
                if child.tag == "classMention":
                    mention_class = child.find("mentionClass")
                    annotations[child.attrib.get("id")].update({
                        "id": mention_class.get("id"),
                        "concept": mention_class.text
                    })
    annotations = sorted(annotations.values(), key=lambda x: x.get("span")[0])
    article = Article(article, annotations, source_id)
    return article


def disjoint_and_overlapping(sentence: Sentence, inplace=True):
    """ Returns a tuple of (
        annotations which do not span over other annotations (disjoint),
        annotations that span over other annotations (overlapping).
    
    Input Params:
    sentence (Sentence): sentence with text and annotations attributes
    
    Return Params:
    (
        disjoint (list): Disjointed list of annotations (empty if None)
        overlapping (list): overlapping annotations (empty if None)
    )

    E.g.
    sentence.text: 'The data so far suggest that the ancestral TACC protein played a 
    role in centrosomal/mitotic spindle dynamics.'

    sentence.annotations: [
        {'span': [(73, 84)], 'spanned_text': 'centrosomal', 'id': 'GO:0005813', 'concept': 'centrosome'}
        {'span': [(85, 92)], 'spanned_text': 'mitotic', 'id': 'GO:0007067', 'concept': 'mitotic nuclear division'}
        {'span': [(85, 100)], 'spanned_text': 'mitotic spindle', 'id': 'GO:0072686', 'concept': 'mitotic spindle'}
    ]

    Result:
    disjoint: [
        {'span': [(73, 84)], 'spanned_text': 'centrosomal', 'id': 'GO:0005813', 'concept': 'centrosome'}
    ]

    overlapping: [
        {'span': [(85, 92)], 'spanned_text': 'mitotic', 'id': 'GO:0007067', 'concept': 'mitotic nuclear division'}
        {'span': [(85, 100)], 'spanned_text': 'mitotic spindle', 'id': 'GO:0072686', 'concept': 'mitotic spindle'}
    ]
    """
    annotations = sentence.annotations
    disjoint = []
    for i in range(len(annotations)):
        span_i = annotations[i].span
        start_i, end_i = span_i[0][0], span_i[-1][1]
        overlap = 0
        for j in range(len(annotations)):
            span_j = annotations[j].span
            start_j, end_j = span_j[0][0], span_j[-1][1]
            if start_j <= start_i < end_j or start_j <= end_i < end_j or \
                start_i <= start_j < end_i or start_i <= end_j < end_i:
                overlap += 1
        if overlap <= 1:
            disjoint.append(annotations[i])
    disjoint = sorted(disjoint, key=lambda k: k.span[0][0], reverse=True)
    overlapping = [i for i in annotations if i not in disjoint]
    overlapping = sorted(overlapping, key=lambda k: k.span[0][0])
    return disjoint, overlapping