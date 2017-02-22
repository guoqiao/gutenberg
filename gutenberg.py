import json
from collections import defaultdict

from dateutil.parser import parser
import rdflib
from path import Path

from xml2json import xml2json

def print_json(obj):
    print(json.dumps(obj, indent=4))

def get_value(obj):
    return obj['Description']['value']

def convert_file_json(obj):
    """
    {
        "modified": "2016-11-04T02:52:05.842547",
        "format": {
            "Description": {
                "value": "application/epub+zip",
                "memberOf": null
            }
        },
        "extent": "190216",
        "isFormatOf": null
    }
    -->
    {
        "modified": datetime(...),
        "format": "application/epub+zip",
        "extent": 190216,
    }
    """
    print_json(obj)
    return {
        'modified': parser(obj['modified']),
        'extent': int(obj['extent']),
        'format': get_value(obj['format'][0]),
    }


def convert_json(rdf_json):
    data = {}
    ebook_json = rdf_json['RDF']['ebook']
    data['subjects'] = [get_value(obj) for obj in ebook_json['subject']]
    data['type'] = get_value(ebook_json['type'])
    data['files'] = [convert_file_json(obj['file']) for obj in ebook_json['hasFormat']]

    return data

def parse_gutenberg_rdf(rdf_path):
    rdf_path = Path(rdf_path)

    graph = rdflib.Graph()
    graph.load(rdf_path)

    rdf_json = xml2json(rdf_path.text())
    data = convert_json(rdf_json)
    # TODO: add missing data from rdflib
    return data

class GutenbergRdfParser:
    """
    Parse a rdf file to json
    """

    def __init__(self, rdf_path=None):
        self.graph = rdflib.Graph()
        self.load(rdf_path)

    def load(self, rdf_path):
        if rdf_path:
            self.rdf_path = Path(rdf_path)
            self.graph.load(rdf_path)
            self.data = {}
            self.tree = self.build_tree()
            self.raw_json = xml2json(self.rdf_path.text())

    def build_tree(self):
        tree = defaultdict(dict)
        for t in self.graph:
            s, p, o = (str(i) for i in t)
            if p not in tree[s]:
                tree[s][p] = []
            tree[s][p].append(o)
        return tree

    def get_id(self):
        """
        get 6899 from pg6899.rdf
        """
        self.id = int(self.rdf_path.namebase[2:])



def parse(uri):
    data = {}
    g = rdflib.Graph()
    g.load(uri)
    id = uri.split('/')[-1].split('.')[0][2:]
    print('id: {}'.format(id))

    has_format = URIRef('http://purl.org/dc/terms/hasFormat')

    for _, file in g.subject_objects(predicate=has_format):
        print(repr(file))
        for attr, value in g.predicate_objects(file):
            repr('{}: {}'.format(attr, value))
        break


if __name__ == '__main__':
    print_json(parse_gutenberg_rdf('samples/pg6899.rdf'))
