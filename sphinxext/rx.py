# -*- coding: utf-8 -*-

"""
    sphinxext.rx
    ~~~~~~~~~~~~

    Sphinx documentation generator for the Rx schema system.

    :copyright: (c)2013 Park Joon-Kyu <segfault@nexon.co.kr>
    :license: BSD

"""


from docutils import nodes
from docutils.parsers.rst import Directive, directives

from sphinx import addnodes
from sphinx.domains import Domain
from sphinx.directives import ObjectDescription
from sphinx.domains import Domain, ObjType, Index
from sphinx.locale import l_, _
from sphinx.roles import XRefRole


# scalar types
__typedesc__ = {
    '//str': 'string',
    '//num': 'number',
    '//int': 'integer',
    '//bool': 'boolean',
    '//one': 'any value but null',
    '//nil': 'null',
    '//def': 'any value',
}


def _is_compositional(type):
    return type == '//arr' or type == '//map'


def _is_sequential(type):
    return type == '//seq'


def _describe_type(_type, node, **kwargs):
    if not isinstance(_type, str) and not isinstance(_type, unicode):
        _type = _type.astext()
    if not _type.startswith('/'):
        node += nodes.inline('', _type)
    elif _type in __typedesc__:
        node += nodes.inline('', _(__typedesc__[_type]))
    elif _is_compositional(_type) and 'contains' in kwargs:
        if _type == '//arr':
            node += nodes.inline('', _('array of '))
        elif  _type == '//map':
            node += nodes.inline('', _('map of '))
        _describe_type(kwargs['contains'], node)
    else:
        node += nodes.inline('', _type)
        #return addnodes.pending_xref('', refdomain='rx', refexplicit=False,
        #                             reftype='schema', reftarget=type)
                        


def _is_single_paragraph(node):
    """True if the node only contains one paragraph (and system messages)."""
    if len(node) == 0:
        return False
    elif len(node) > 1:
        for subnode in node[1:]:
            if not isinstance(subnode, nodes.system_message):
                return False
    if isinstance(node[0], nodes.paragraph):
        return True
    return False


class RxTransformer(object):

    def __init__(self, directive):
        self.domain = directive.domain        

    def transform_all(self, node):
        for child in node:
            if isinstance(child, nodes.field_list):
                self.transform(child)

    def transform(self, node):
        raise NotImplementedError


class RxNamedFieldTransformer(RxTransformer):

    def transform(self, node):
        """Transform named field(s) into desired manner."""

        fields = []
        fieldargs = {}
        
        # The input can be in arbitrary order so sort it out
        for field in node:
            fieldname, fieldbody = field
            try:
                fieldtype, fieldarg = fieldname.astext().split(None, 1)
            except ValueError:
                fieldtype, fieldarg = fieldname.astext(), ''
            if fieldtype == 'field':
                fields.append((fieldarg, fieldbody))
            else:
                assert fieldarg is not None
                if not fieldarg in fieldargs:
                    fieldargs[fieldarg] = {}
                fieldargs[fieldarg][fieldtype] = fieldbody
        if len(fields) == 0:
            return

        new_list = nodes.field_list()
        field_name = nodes.field_name('', _('Fields'))
        list = nodes.bullet_list()
        for name, body in fields:
            header = []
            if not name in fieldargs:
                fieldargs[name] = {}
            options = fieldargs[name]
            if 'requires' in options and \
                    options['requires'].astext().lower() == 'yes':
                header.append(nodes.strong('', name))
            else:
                header.append(nodes.emphasis('', name))
            if 'type' in options:
                header.append(nodes.inline('', ' ('))
                n = nodes.inline()
                _describe_type(options['type'].astext(), n, **fieldargs[name])
                header.extend(n)
                header.append(nodes.inline('', ')'))
            header.append(nodes.inline('', ' -- '))
            list += nodes.list_item('', *(header + body.children[0].children))
        field_body = nodes.field_body('', list)
        new_list += nodes.field('', field_name, field_body)

        node.replace_self(new_list)


class RxFieldListTransformer(RxTransformer):

    list_type = NotImplemented

    def transform(self, node):
        """This one should be used with unnamed fields."""

        fields = []
        fieldargs = {}
        
        # Pack into
        index = -1
        for field in node:
            fieldname, fieldbody = field
            fieldtype = fieldname.astext()
            if fieldtype == 'field':
                index += 1
                fields.append(fieldbody)
            else:
                assert index >= 0
                if not index in fieldargs:
                    fieldargs[index] = {}
                fieldargs[index][fieldtype] = fieldbody
        if len(fields) == 0:
            return

        new_list = nodes.field_list()
        field_name = nodes.field_name('', _('Fields'))
        list = nodes.bullet_list()
        for index, body in enumerate(fields):
            footer = []
            if not index in fieldargs:
                fieldargs[index] = {}
            options = fieldargs[index]
            if 'type' in options:
                footer.append(nodes.inline('', ' ('))
                n = nodes.inline()
                _describe_type(options['type'].astext(), n, **fieldargs[index])
                footer.extend(n)
                footer.append(nodes.inline('', ')'))
            if 'requires' in options and \
                    options['requires'].astext().lower() == 'yes':
                content = nodes.strong()
            else:
                content = nodes.inline()
            content += body.children[0].children
            list += nodes.list_item('', content, *footer)
        field_body = nodes.field_body('', list)
        new_list += nodes.field('', field_name, field_body)

        node.replace_self(new_list)


class RxCollectionTransformer(RxFieldListTransformer):
    
    list_type = nodes.bullet_list


class RxSequentialTransformer(RxFieldListTransformer):
    
    list_type = nodes.enumerated_list


__transformers__ = {
    '//rec': RxNamedFieldTransformer,
    '//any': RxCollectionTransformer,
    '//all': RxCollectionTransformer,
    '//seq': RxSequentialTransformer,
}


class RxSchemaDirective(Directive):

    has_content = True
    required_arguments = 1
    final_argument_whitespace = True
    
    option_spec = {
        'type': lambda x: str(x),
        'requires': lambda x: directives.choice(x, ('yes', 'no')),
        'contains': lambda x: str(x),
    }

    def run(self):
        if ':' in self.name:
            self.domain, self.objtype = self.name.split(':', 1)
        else:
            self.domain, self.objtype = '', self.name
        self.env = self.state.document.settings.env
        self.indexnode = addnodes.index(entries=[])

        node = addnodes.desc()
        node.document = self.state.document
        node['domain'] = self.domain
        node['objtype'] = node['desctype'] = self.objtype
        node['noindex'] = False

        try:
            signature = self.arguments[0]
            if self.objtype == 'schema':
                signode = addnodes.desc_signature(signature)
                signode['first'] = False
                node += signode
        except:
            signature = None

        headernode = addnodes.desc_name()
        headernode += nodes.inline('', _(self.objtype) + ' ')
        if signature is not None:
            headernode += nodes.emphasis('', signature)
        if _is_compositional(self.options['type']):
            if signature is not None:
                headernode += nodes.inline('', ' -- ')
            _describe_type(self.options['type'], headernode,
                           contains=self.options['contains'])
        node.append(headernode)

        contentnode = addnodes.desc_content()
        node.append(contentnode)
        self.state.nested_parse(self.content, self.content_offset, contentnode)
        type = self.options['type']
        if type in __transformers__:
            __transformers__[type](self).transform_all(contentnode)

        return [addnodes.index(entries=[]), node]


class RxFieldDirective(RxSchemaDirective):
    
    required_arguments = 0
    optional_arguments = 1


class RxXRefRole(XRefRole):

    def process_link(self, env, refnode, has_explicit_title,
                     title, target):
        print title, target
        return title, target


class RxDomain(Domain):

    """RX domain."""

    name = 'rx'
    label = 'Rx'

    object_types = {
        'schema': ObjType('schema', 'type'),
        'field': ObjType('schema', 'type'),
    }

    directives = {
        'schema': RxSchemaDirective,
        'field': RxFieldDirective,
    }

    roles = {
        'schema': RxXRefRole(),
        'field': RxXRefRole(),
    }


def setup(app):
    app.add_domain(RxDomain)
