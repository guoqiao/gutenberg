import json
from datetime import datetime
from collections import defaultdict

from dateutil.parser import parser
import rdflib
from path import Path

from xml2json import xml2json


DT_LEN = len('2016-11-04T02:52:10')
DT_FMT = '%Y-%m-%dT%H:%M:%S'


def get_dt(s):
    return datetime.strptime(s[:DT_LEN], DT_FMT)


def print_json(obj):
    print(json.dumps(obj, indent=4))


def get_value(obj):
    """
    Extract value from obj.

    "Description": {
        "value": "application/epub+zip",
        "memberOf": null
    }
    """
    return obj['Description']['value']


def get_values(obj):
    if isinstance(obj, list):
        return [get_value(item) for item in obj]
    else:
        return [get_value(obj)]


def refine_format_json(obj):
    """
    {
        "modified": "2016-11-04T02:52:05.842547",
        "extent": "190216",
        "isFormatOf": null
        "format": {
            "Description": {
                "value": "application/epub+zip",
                "memberOf": null
            }
        },
    }
    or:
    "modified": "2014-03-19T20:25:06",
    "isFormatOf": null,
    "extent": "177281"
    "format": [
        {
            "Description": {
                "memberOf": null,
                "value": "text/plain; charset=us-ascii"
            }
        },
        {
            "Description": {
                "value": "application/zip",
                "memberOf": null
            }
        }
    ],
    -->
    {
        "modified": datetime(...),
        "format": "application/epub+zip",
        "extent": 190216,
    }
    """
    return {
        'modified_at': obj['modified'][:DT_LEN],
        'size': int(obj['extent']),
        'formats': get_values(obj['format']),
    }


def refine_rdf_json(rdf_json):
    data = {}
    ebook_json = rdf_json['RDF']['ebook']
    data['subjects'] = [get_value(obj) for obj in ebook_json['subject']]
    data['files'] = [refine_format_json(obj['file']) for obj in ebook_json['hasFormat']]

    data['author'] = ebook_json['creator']['agent']

    data['type'] = get_value(ebook_json['type'])
    data['language'] = get_value(ebook_json['language'])

    data['downloads'] = ebook_json['downloads']
    data['title'] = ebook_json['title']
    data['issued'] = ebook_json['issued']

    data['bookshelf'] = get_values(ebook_json['bookshelf'])

    return data

def parse_gutenberg_rdf(rdf_path):
    rdf_path = Path(rdf_path)

    graph = rdflib.Graph()
    graph.load(rdf_path)

    rdf_json = xml2json(rdf_path.text())
    data = refine_rdf_json(rdf_json)
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
    print_json(parse_gutenberg_rdf('samples/pg60.rdf'))
