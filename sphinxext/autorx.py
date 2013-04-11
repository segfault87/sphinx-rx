# -*- coding: utf-8 -*-

"""
    sphinxext.autorx
    ~~~~~~~~~~~~

    Sphinx documentation generator for the Rx schema system.

    :copyright: (c)2013 Park Joon-Kyu <segfault87@gmail.com>
    :license: BSD

"""

from docutils import nodes
from docutils.statemachine import ViewList

from sphinx.util import force_decode
from sphinx.util.compat import Directive
from sphinx.util.nodes import nested_parse_with_titles
from sphinx.util.docstrings import prepare_docstring

from functools import wraps
import yaml
import json


def decapitalize_first(s):
    if len(s) == 0: return ''
    return s[0].lower() + s[1:]


def spc(n, v):
    return ' '*n + v


def is_scalar(v):
    if type(v) == str:
        return True
    else:
        if v['type'] in SCALAR and not 'doc' in v:
            return True
    return False


def describe_range(range):
    start = ''
    end = ''
    if 'min' in range:
        start = '%s < ' % range['min']
    elif 'min-ex' in range:
        start = '%s ≤ ' % range['min-ex']
    if 'max' in range:
        end = ' < %s' % range['max']
    elif 'max-ex' in range:
        end = ' ≤ %s' % range['max-ex']
    return '%sn%s' % (start, end)


def describe_number(node):
    if 'range' in node:
        if type(node) == dict:
            return 'the value must in %s' % describe_range(node['range'])
        else:
            return 'the value must be %s' % node['range']
    elif 'value' in node:
        return 'the value must be %s' % node['value']


def describe_doc(node, depth):
    if type(node) != dict or not 'doc' in node:
        return
    for line in node['doc'].split('\n'):
        yield line
    yield ''


def describe(f):
    @wraps(f)
    def decorated(node, depth):
        for l in f(node, depth):
            yield spc(depth, l)
        for l in describe_doc(node, depth):
            yield spc(depth, l)
    return decorated


@describe
def read_all(node, depth):
    yield 'Should satisfy every of following:'
    yield ''
    for clause in node['of']:
        of = read_node(clause, 2)
        yield '- %s' % of.next().strip()
        for l in of:
            yield l


@describe
def read_any(node, depth):
    yield 'Should be one of following:'
    yield ''
    for clause in node['of']:
        of = read_node(clause, 2)
        yield '- %s' % of.next().strip()
        for l in of:
            yield l


@describe
def read_arr(node, depth):
    hint = None
    if 'length' in node:
        length = node['length']
        if type(length) == dict:
            length = describe_range(length)
        hint = 'The length must be %s.' % length
    contents = read_node(node['contents'], 0)
    yield 'Array consisted of %s' % decapitalize_first(contents.next())
    for l in contents:
        yield l
    if hint:
        yield hint
        yield ''


@describe
def read_bool(node, depth):
    yield 'Boolean (true or false)'
    yield ''


@describe
def read_def(node, depth):
    yield 'Any value'
    yield ''


@describe
def read_int(node, depth):
    if type(node) == dict:
        hint = describe_number(node)
        if hint is not None:
            yield 'Integer *(%s)*' % hint
            yield ''
            return
    yield 'Integer'
    yield ''


@describe
def read_map(node, depth):
    value = read_node(node['values'], 0)
    yield 'Collections of key/value pair.'
    yield ''
    yield 'The key must be string and the value must be %s' % \
        decapitalize_first(value.next())
    yield ''
    for l in value:
        yield l


@describe
def read_nil(node, depth):
    yield 'Null value'
    yield ''


@describe
def read_num(node, depth):
    if type(node) == dict:
        hint = describe_number(node)
        if hint is not None:
            yield 'A number *(%s)*' % hint
            yield ''
            return
    yield 'Number'
    yield ''


@describe
def read_one(node, depth):
    yield 'Any scalar value *(string, number, integer, boolean)*'
    yield ''


@describe
def read_rec(node, depth):
    yield 'Record. Consisted elements are:'
    yield ''
    if 'required' in node:
        for k, v in node['required'].iteritems():
            if is_scalar(v):
                yield '- **%s** (required): %s' % (k, read_node(v, 0).next())
                yield ''
            else:
                yield '- **%s** (required):' % k
                yield ''
                for l in read_node(v, 2):
                    yield l
    elif 'optional' in node:
        for k, v in node['optional'].iteritems():
            if is_scalar(v):
                yield '- *%s*: %s' % (k, read_node(v, 0).next())
                yield ''
            else:
                yield '- *%s*:' % k
                yield ''
                for l in read_node(v, 2):
                    yield l
                    

@describe
def read_seq(node, depth):
    contents = node['contents']
    if 'tail' in node:
        yield 'Array. First %d items must be:' % len(contents)
    else:
        yield 'Array with %d items. Each items must be:' % len(contents)
    yield ''
    for content in contents:
        subschema = read_node(content, 0)
        yield '#) %s' % subschema.next()
        yield ''
        for i in subschema:
            yield '   ' + i
    if 'tail' in node:
        tailschema = read_node(node['tail'], 0)
        yield 'And the rest must be %s' % decapitalize_first(tailschema.next())
        yield ''
        for i in tailschema:
            yield i


@describe
def read_str(node, depth):
    if type(node) == dict:
        hint = None
        if 'value' in node:
            hint = 'the content must be *%s*' % node['value']
        elif 'length' in node:
            if type(node['length']) == dict:
                hint = 'the length of string must be %s' % describe_range(node['length'])
            else:
                hint = 'the length of string must be %s characters long' % node['length']
        if hint is not None:
            yield 'String *(%s)*' % hint
            yield ''
            return
    yield 'String'
    yield ''


NODES = {'//all': read_all,
         '//any': read_any,
         '//arr': read_arr,
         '//bool': read_bool,
         '//def': read_def,
         '//int': read_int,
         '//map': read_map,
         '//nil': read_nil,
         '//num': read_num,
         '//one': read_one,
         '//rec': read_rec,
         '//seq': read_seq,
         '//str': read_str}


SCALAR = frozenset(('//nil', '//def', '//bool', '//num',
                    '//int', '//str', '//one'))


def read_node(node, depth):
    if type(node) == str:
        if node in NODES:
            for l in NODES[node](node, depth):
                yield l
                return
        yield '---- link to %s ---' % node
    elif node['type'] in NODES:
        for l in NODES[node['type']](node, depth):
            yield l

                
def read(document):
    for l in read_node(document, 0):
        yield l


class RxDirective(Directive):
    
    has_content = True
    required_arguments = 1
    option_spec = {'path': str,
                   'document-type': str}

    @property
    def path(self):
        return self.options['path']

    @property
    def document_type(self):
        try:
            return self.options['document-type']
        except:
            return 'yaml'

    def make_rst(self):
        name = self.arguments[0]
        document = yaml.load(open(self.path, 'r').read())
        for l in read(document):
            yield l.decode('utf-8')

    def run(self):
        assert self.document_type in ['yaml', 'json']
        node = nodes.section()
        node.document = self.state.document
        result = ViewList()
        for line in self.make_rst():
            result.append(line, '<rx>')
        nested_parse_with_titles(self.state, result, node)
        return node.children


def setup(app):
    app.add_directive('autorx', RxDirective)


if __name__ == '__main__':
    import sys
    doc = yaml.load(open(sys.argv[1], 'r').read())
    for l in read(doc):
        print l
