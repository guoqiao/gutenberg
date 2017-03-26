"""
Parse a RDF file from Gutenburg.

Convert all RDF value to python string and dict.
Keep value as it is.
e.g.: do not convert datetime, int, or file format.
"""
import json
from datetime import datetime
from collections import defaultdict, OrderedDict

from dateutil.parser import parser
import rdflib
from rdflib.term import *
from path import Path

from xml2json import xml2json


def print_json(obj):
    print(json.dumps(obj, indent=4))


def get_uri_to_attrs(rdf_path):
    """
    Parse a RDF file, return uri to attrs map for files.

    {
        "http://www.gutenberg.org/ebooks/6899.epub.noimages": {
            "format": "Nc7e95e2ac95b4df4975b9e0bacaaa148",
            "modified": "2016-11-04T02:52:06.208530",
            "extent": "190216",
            "isFormatOf": "6899",
            "22-rdf-syntax-ns#type": "file"
        },
        "http://www.gutenberg.org/files/6899/6899-h/6899-h.htm": {
            "modified": "2014-03-19T20:24:24",
            "format": "Nec6b6e616be54479b408f12e6dec6dfd",
            "extent": "504553",
            "isFormatOf": "6899",
            "22-rdf-syntax-ns#type": "file"
        },
    ...
    }
    """
    g = rdflib.Graph()
    g.load(rdf_path)
    has_format = URIRef('http://purl.org/dc/terms/hasFormat')
    uri_to_attrs = {}
    for _, uriref in g.subject_objects(predicate=has_format):
        uri_to_attrs[str(uriref)] = {str(attr).split('/')[-1]: str(value).split('/')[-1] for attr, value in g.predicate_objects(uriref)}
    return uri_to_attrs


def get_attrs_to_uri(uri_to_attrs):
    """
    Convert a `uri_to_attrs` map to `attrs_to_uri` map.

    {
        "2016-11-04T02:52:06.208530-190216": "http://www.gutenberg.org/ebooks/6899.epub.noimages",
        "2014-03-19T20:25:06-177281": "http://www.gutenberg.org/files/6899/6899.zip",
        "2014-03-19T20:24:12-475988": "http://www.gutenberg.org/files/6899/6899.txt",
        ...
    }
    """
    return {
        '{}-{}'.format(attrs['modified'], attrs['extent']): uri
        for uri, attrs in uri_to_attrs.items()
    }



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


def normalize_file_json(obj, attrs_to_uri):
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
        "modified": "2014-03-19T20:25:06",
        "format": ["application/epub+zip", "text/plain; charset=us-ascii"],
        "extent": 190216,
    }
    """
    return {
        'modified_at': obj['modified'],
        'size': obj['extent'],
        'formats': get_values(obj['format']),
        'uri': attrs_to_uri['{}-{}'.format(obj['modified'], obj['extent'])]
    }


def normalize_rdf_json(rdf_path):

    rdf_path = Path(rdf_path)
    rdf_json = xml2json(rdf_path.text())

    data = OrderedDict()
    data['id'] = rdf_path.split('/')[-1].split('.')[0][2:]

    ebook_json = rdf_json['RDF']['ebook']

    data['title'] = ebook_json['title']
    data['issued'] = ebook_json['issued']

    data['type'] = get_value(ebook_json['type'])
    data['language'] = get_value(ebook_json['language'])
    data['downloads'] = ebook_json['downloads']

    data['subjects'] = get_values(ebook_json['subject'])
    data['bookshelves'] = get_values(ebook_json['bookshelf'])

    data['author'] = ebook_json['creator']['agent']

    # map from attrs to uri
    attrs_to_uri = get_attrs_to_uri(get_uri_to_attrs(rdf_path))

    data['files'] = [
        normalize_file_json(obj['file'], attrs_to_uri)
        for obj in ebook_json['hasFormat']
    ]

    return data


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Parse Gutenberg RDF file')
    parser.add_argument('path', help='Path to a rdf file')
    args = parser.parse_args()
    print_json(normalize_rdf_json(args.path))
