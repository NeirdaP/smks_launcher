from html.parser import HTMLParser
from html.entities import name2codepoint
import xml.etree.ElementTree as ET


class MyHTMLParser(HTMLParser):

    def __init__(self, *args, convert_charrefs=True):
        super(MyHTMLParser, self).__init__(*args, convert_charrefs=convert_charrefs)
        self._root = ET.fromstring("<root></root>")
        self._root.text = ""
        self._element_stack = []

    def _conform_attrs(self, attrs):
        return dict((k, v if v is not None else '') for k, v in attrs)

    def handle_starttag(self, tag, attrs):
        e = ET.SubElement(self._element_stack[-1] if self._element_stack else self._root,
                                tag, self._conform_attrs(attrs))
        e.text = ""
        self._element_stack.append(e)

    def handle_endtag(self, tag):
        self._element_stack.pop(-1)

    def handle_startendtag(self, tag, attrs):
        e = ET.SubElement(self._element_stack[-1] if self._element_stack else self._root, tag, self._conform_attrs(attrs))
        e.text = ""

    def handle_data(self, data):
        data = data.replace('\t', '')
        if data and self._element_stack:
            self._element_stack[-1].text += data

    def find(self, path):
        return self._root.find(path)

    def root(self):
        return self._root

    def __str__(self):
        return ET.tostring(self._root.find("html"), encoding='unicode', method="html")

    def to_string(self):
        return ET.tostring(self._root.find("html"), encoding='unicode', method="html")
