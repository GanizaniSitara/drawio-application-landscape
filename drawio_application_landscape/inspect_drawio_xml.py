import drawio_tools
import lxml.etree as etree
from xml.etree import ElementTree
import sys

x = etree.parse(sys.argv[1])
#print(etree.tostring(x, pretty_print=True))

diagram_data = x.findall('.//diagram')[0]#.text
#print(diagram_data)
diagram_data = ElementTree.tostring(diagram_data).decode('utf8')
print(diagram_data)



