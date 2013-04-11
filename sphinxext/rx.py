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
from sphinx.util.docfields import DocFieldTransformer, Field, GroupedField


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


class RxRecTransformer(RxTransformer):

    def transform(self, node):
        fields = []
        fieldargs = {}
        
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

    def _transform(self, node):
        typemap = self.typemap

        entries = []
        groupindices = {}
        types = {}

        for field in node:
            fieldname, fieldbody = field
            try:
                fieldtype, fieldarg = fieldname.astext().split(None, 1)
            except ValueError:
                fieldtype, fieldarg = fieldname.astext(), ''
            typedesc, is_typefield = typemap.get(fieldtype, (None, None))

            if typedesc is None or typedesc.has_arg != bool(fieldarg):
                new_fieldname = fieldtype.capitalize() + ' ' + fieldarg
                fieldname[0] = nodes.Text(new_fieldname)
                entries.append(field)
                continue

            typename = typedesc.name

            if _is_single_paragraph(fieldbody):
                content = fieldbody.children[0].children
            else:
                content = fieldbody.children

            if is_typefield:
                content = filter(
                    lambda n: isinstance(n, nodes.Inline) or
                              isinstance(n, nodes.Text),
                    content)
                if content:
                    types.setdefault(typename, {})[fieldarg] = content
                continue

            if typedesc.is_typed:
                try:
                    argtype, argname = fieldarg.split(None, 1)
                except ValueError:
                    pass
                else:
                    types.setdefault(typename, {})[argname] = \
                                               [nodes.Text(argtype)]
                    fieldarg = argname

            translatable_content = nodes.inline(fieldbody.rawsource,
                                                translatable=True)
            translatable_content.source = fieldbody.parent.source
            translatable_content.line = fieldbody.parent.line
            translatable_content += content

            if typedesc.is_grouped:
                if typename in groupindices:
                    group = entries[groupindices[typename]]
                else:
                    groupindices[typename] = len(entries)
                    group = [typedesc, []]
                    entries.append(group)
                entry = typedesc.make_entry(fieldarg, translatable_content)
                group[1].append(entry)
            else:
                entry = typedesc.make_entry(fieldarg, translatable_content)
                entries.append([typedesc, entry])

        new_list = nodes.field_list()
        for entry in entries:
            if isinstance(entry, nodes.field):
                new_list += entry
            else:
                fieldtype, content = entry
                fieldtypes = types.get(fieldtype.name, {})
                new_list += fieldtype.make_field(fieldtypes, self.domain,
                                                 content)

        node.replace_self(new_list)


__transformers__ = {
    '//rec': RxRecTransformer
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

        self.names = []
        signature = self.arguments[0]
        signode = addnodes.desc_signature(signature)
        signode['first'] = False
        node.append(signode)
        self.names.append(signature)

        headernode = addnodes.desc_name()
        headernode += nodes.Text('schema ', 'schema ')
        headernode += nodes.emphasis(signature, signature)
        node.append(headernode)

        contentnode = addnodes.desc_content()
        node.append(contentnode)
        if self.name:
            self.env.temp_data['object'] = self.names[0]
        self.state.nested_parse(self.content, self.content_offset, contentnode)
        type = self.options['type']
        if type in __transformers__:
            __transformers__[type](self).transform_all(contentnode)

        return [addnodes.index(entries=[]), node]

class RxFieldDirective(RxSchemaDirective):
    pass


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
