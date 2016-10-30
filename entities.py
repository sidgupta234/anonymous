# Code from https://pythonprogramming.net/using-bio-tags-create-named-entity-lists/
import os
import configparser
from nltk import pos_tag
from nltk.tag import StanfordNERTagger
from nltk.tokenize import word_tokenize
from nltk.chunk import conlltags2tree
from nltk.tree import Tree


config = configparser.ConfigParser()
config.read("config.ini")
MY_CLASSIFIER = config.get("Stanford", "classifier_file")
MY_JAR = config.get("Stanford", "jar_file")
JAVA_PATH = config.get("Stanford", "java_path")
os.environ['JAVAHOME'] = JAVA_PATH


# TODO: Make database call here
txt_file = "C:/Temp/news_article.txt"


def process_text(txt):
    raw_text = open(txt).read()
    token_text = word_tokenize(raw_text)
    return token_text


def stanford_tagger(token_text):
    st = StanfordNERTagger(MY_CLASSIFIER,
                           MY_JAR,
                           encoding='utf-8')
    ne_tagged = st.tag(token_text)
    return ne_tagged


# Tag tokens with standard NLP BIO tags
def bio_tagger(ne_tagged):
    bio_tagged = []
    prev_tag = "O"
    for token, tag in ne_tagged:
        if tag == "O":  # O
            bio_tagged.append((token, tag))
            prev_tag = tag
            continue
        if tag != "O" and prev_tag == "O":  # Begin NE
            bio_tagged.append((token, "B-" + tag))
            prev_tag = tag
        elif prev_tag != "O" and prev_tag == tag:  # Inside NE
            bio_tagged.append((token, "I-" + tag))
            prev_tag = tag
        elif prev_tag != "O" and prev_tag != tag:  # Adjacent NE
            bio_tagged.append((token, "B-" + tag))
            prev_tag = tag
    return bio_tagged


def stanford_tree(bio_tagged):
    tokens, ne_tags = zip(*bio_tagged)
    pos_tags = [pos for token, pos in pos_tag(tokens)]

    conlltags = [(token, pos, ne) for token, pos, ne in zip(tokens, pos_tags, ne_tags)]
    ne_tree = conlltags2tree(conlltags)
    return ne_tree


# Parse named entities from tree
def structure_ne(ne_tree):
    ne = []
    for subtree in ne_tree:
        if type(subtree) == Tree:  # If subtree is a noun chunk, i.e. NE != "O"
            ne_label = subtree.label()
            ne_string = " ".join([token for token, pos in subtree.leaves()])
            ne.append((ne_string, ne_label))
    return ne


def get_entities():
    return structure_ne(stanford_tree(bio_tagger(stanford_tagger(process_text(txt_file)))))


if __name__ == '__main__':
    my_entities = get_entities()
    print(my_entities[3])