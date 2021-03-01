#
#   This file is part of m.css.
#
#   Copyright © 2017, 2018, 2019, 2020 Vladimír Vondruš <mosra@centrum.cz>
#
#   Permission is hereby granted, free of charge, to any person obtaining a
#   copy of this software and associated documentation files (the "Software"),
#   to deal in the Software without restriction, including without limitation
#   the rights to use, copy, modify, merge, publish, distribute, sublicense,
#   and/or sell copies of the Software, and to permit persons to whom the
#   Software is furnished to do so, subject to the following conditions:
#
#   The above copyright notice and this permission notice shall be included
#   in all copies or substantial portions of the Software.
#
#   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#   IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#   FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
#   THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#   LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#   FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#   DEALINGS IN THE SOFTWARE.
#

import re
import subprocess

# <?xml version="1.0" encoding="UTF-8" standalone="no"?><svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" contentScriptType="application/ecmascript" contentStyleType="text/css" height="561.4583px" preserveAspectRatio="none" style="width:632px;height:561px;" version="1.1" viewBox="0 0 632 561" width="632.2917px" zoomAndPan="magnify">
_patch_src = re.compile(r"""(<\?xml version="1\.0" encoding="UTF-8" standalone="no"\?>)?<svg xmlns="http://www\.w3\.org/2000/svg" xmlns:xlink="http://www\.w3\.org/1999/xlink" contentScriptType="application/ecmascript" contentStyleType="text/css" height="(?P<height>\d+(\.\d+)?)px" preserveAspectRatio="none" style="width:(\d+(\.\d+)?)px;height:(\d+(\.\d+)?)px;" version="1\.1" viewBox="(?P<viewBox>[^"]+)" width="(?P<width>\d+(\.\d+)?)px" zoomAndPan="magnify">""")

_patch_custom_size_dst = r"""<svg{attribs} style="{size}" viewBox="\g<viewBox>">"""

_comment_src = re.compile(r"""<!--((?!-->).|\s)*-->""")

# Graphviz < 2.40 (Ubuntu 16.04 and older) doesn't have a linebreak between <g>
# and <title>
_class_src = re.compile(r"""<g id="(edge|node|clust)\d+" class="(?P<type>edge|node|cluster)(?P<classes>[^"]*)">[\n]?<title>(?P<title>[^<]*)</title>
<(?P<element>ellipse|polygon|path|text)( fill="(?P<fill>[^"]+)" stroke="[^"]+")? """)

_class_dst = r"""<g class="{classes}">
<title>{title}</title>
<{element} """

_attributes_src = re.compile(r"""<(?P<element>ellipse|polygon|polyline) fill="[^"]+" stroke="[^"]+" """)

_attributes_dst = r"""<\g<element> """

_additional_params = []
_background = None

_plantuml_jar_path = None

def plantuml2svg(source, size=None, attribs=''):
    if _plantuml_jar_path is None:
        raise RuntimeError("PLANTUML_JAR_PATH not set")
    try:
        ret = subprocess.run(['java', '-jar', _plantuml_jar_path, '-tsvg', "-pipe"] + _additional_params,
                             input=source.encode('utf-8'), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if ret.returncode: print(ret.stderr.decode('utf-8'))
        ret.check_returncode()
    except FileNotFoundError: # pragma: no cover
        raise RuntimeError("plantuml not found")

    # First remove comments
    svg = _comment_src.sub('', ret.stdout.decode('utf-8'))

    if _patch_src.match(svg) is None:
        print(svg)

    # Remove preamble and fixed size
    if size:
        svg = _patch_src.sub(_patch_custom_size_dst.format(attribs=attribs, size=size), svg)

    # Remove unnecessary IDs and attributes, replace classes for elements
    def element_repl(match):
        classes = ['m-' + match.group('type')] + match.group('classes').replace('&#45;', '-').split()
        # distinguish between solid and filled nodes
        if ((match.group('type') == 'node' and match.group('fill') == 'none') or
            # a plaintext node is also flat
            match.group('element') == 'text'
        ):
            classes += ['m-flat']

        return _class_dst.format(
            classes=' '.join(classes),
            title=match.group('title'),
            element=match.group('element'))
    svg = _class_src.sub(element_repl, svg)

    # Remove unnecessary fill and stroke attributes
    svg = _attributes_src.sub(_attributes_dst, svg)

    return svg

def configure(plantuml_jar_path, additional_params = None, background = None):
    global _plantuml_jar_path, _additional_params, _background

    _plantuml_jar_path = plantuml_jar_path

    if _additional_params is not None:
        _additional_params = additional_params.split(' ')
    if _background is not None:
        _background = background

