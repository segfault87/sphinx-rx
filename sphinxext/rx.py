# -*- coding: utf-8 -*-

"""
    sphinxext.rx
    ~~~~~~~~~~~~

    Sphinx documentation generator for the Rx schema system.

    :copyright: (c)2013 Park Joon-Kyu <segfault@nexon.co.kr>
    :license: BSD

"""


from docutils import nodes
from docutils.parsers.rst import Directive

from sphinx import addnodes
from sphinx.domains import Domain
from sphinx.directives import ObjectDescription
from sphinx.domains import Domain, ObjType, Index
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


class RxFieldTransformer(object):
    def __init__(self, directive):
        self.domain = directive.domain
        if '_doc_field_type_map' not in directive.__class__.__dict__:
            directive.__class__._doc_field_type_map = \
                self.preprocess_fieldtypes(directive.__class__.doc_field_types)
        self.typemap = directive._doc_field_type_map

    def preprocess_fieldtypes(self, types):
        typemap = {}
        for fieldtype in types:
            for name in fieldtype.names:
                typemap[name] = fieldtype, False
            if fieldtype.is_typed:
                for name in fieldtype.typenames:
                    typemap[name] = fieldtype, True
        return typemap

    def transform_all(self, node):
        for child in node:
            if isinstance(child, nodes.field_list):
                self.transform(child)

    def transform(self, node):
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
        print entries
        for entry in entries:
            if isinstance(entry, nodes.field):
                new_list += entry
            else:
                fieldtype, content = entry
                fieldtypes = types.get(fieldtype.name, {})
                new_list += fieldtype.make_field(fieldtypes, self.domain,
                                                 content)

        node.replace_self(new_list)


class RxSchemaDirective(Directive):

    has_content = True
    required_arguments = 1
    final_argument_whitespace = True
    
    doc_field_types = [
        GroupedField('type', label='Type',
              names=('type', )),
        GroupedField('field', label='Field',
                     names=('field', )),
        Field('contains', label='Contains',
              names=('contains', )),
        Field('requires', label='Requires',
              names=('requires', )),
    ]

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

        contentnode = addnodes.desc_content()
        node.append(contentnode)
        if self.name:
            self.env.temp_data['object'] = self.names[0]
        self.state.nested_parse(self.content, self.content_offset, contentnode)
        RxFieldTransformer(self).transform_all(contentnode)

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
