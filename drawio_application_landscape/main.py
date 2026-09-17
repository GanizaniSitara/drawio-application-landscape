import logging
from enum import Enum

from lxml import etree
import string
import random

import pandas as pd
import itertools as it
import sys
import math
import csv
import os
from datetime import datetime

# our imports
from drawio_application_landscape import drawio_shared_functions
from drawio_application_landscape import drawio_tools

from drawio_application_landscape.config.config_script import ScriptConfig
from drawio_application_landscape.config.config_diagram import DiagramConfig
from drawio_application_landscape.utils import utils

# currently the EXPERIMENTAL flag turns on the page width limiting feature
# restack of L2's if too wide to fit within page width in one row
EXPERIMENTAL = ScriptConfig.EXPERIMENTAL

MAX_PAGE_WIDTH = DiagramConfig.MAX_PAGE_WIDTH['L1']



# Module level state. main() resets both; they are defined here so the module can be
# imported and driven as a library.
DEBUG = False
swapp_style_builder = None

logger = logging.getLogger(__name__)


class InvalidInput(Exception):
    """The CSV cannot be rendered, and the message says why."""


# Grouping and identity. Every other column is optional.
REQUIRED_COLUMNS = ('Level1', 'Level2', 'AppName')

# Optional columns, and the layer each one drives.
OPTIONAL_COLUMNS = (
    'TC',                # Transaction cycle label
    'StatusRAG',         # red / amber / green, colours the Strategy layer
    'Resilience',        # 0-4, colours the Resilience layer
    'Category',          # accepted as an alias for Resilience
    'Link',              # hyperlink on the application box
    'Controls',          # hyperlink, draws the Controls pictogram
    'HostingPercent',    # 0-100, Harvey ball on the Hosting layer
    'HostingPattern1',   # hosting icon, see HostingPattern
    'HostingPattern2',
    'Arrow1',            # up / down trend arrow on the Metrics layer
    'Arrow2',
    'DecommDate',        # YYYY-MM, shown as a Cease date
)


class Level1:
    def __init__(self, name, x=0, y=0):
        self.name = name
        self.level2s = []
        self.x = x
        self.y = y
        self.placed = False
        self.vertical_spacing = 10
        self.horizontal_spacing = 10
        self.L0_SCALING = 0.5
        self.header_height = DiagramConfig.HEADER_HEIGHT['L1']
        self.reduced_font_size = False

    def size(self):
        return sum([level2.size() for level2 in self.level2s])

    def height(self, transpose=False):
        if EXPERIMENTAL:
            return self.height_new(transpose)

        result = self.header_height
        if not transpose:
            result += max(level2.dimensions(transpose=transpose)[0] for level2 in self.level2s) + self.vertical_spacing
        else:
            for level2 in self.level2s:
                result += level2.dimensions(transpose=transpose)[0] + self.vertical_spacing
        return result

    def height_new(self, transpose=False):
        processed = set()
        total_height = 0
        x_cursor = 0
        max_height_in_row = 0

        for i in range(len(self.level2s)):
            node_id = id(self.level2s[i])

            if node_id in processed:
                pass
            else:
                x_cursor += self.level2s[i].width(transpose) + 10
                max_height_in_row = max(max_height_in_row, self.level2s[i].height(transpose) + 10)
                processed.add(node_id)

                for j in range(i + 1, len(self.level2s)):
                    node_id = id(self.level2s[j])

                    if node_id in processed:
                        continue
                    if x_cursor + self.level2s[j].width(transpose) <= DiagramConfig.MAX_PAGE_WIDTH['L1']:
                        x_cursor += self.level2s[j].width(transpose) + 10
                        max_height_in_row = max(max_height_in_row, self.level2s[j].height(transpose) + 10)
                        processed.add(node_id)
                    else:
                        x_cursor = 0
                        break

            total_height += max_height_in_row
            max_height_in_row = 0

        return total_height + self.header_height

    def width_new(self, transpose=False):
        # new implementation that runs the dynamic build of L2 to work out page size packing
        # the sequence is the same as what places items on the page in L1.appender(), can be factored out later
        processed = set()
        max_width = 0
        x_cursor = 0

        for i in range(len(self.level2s)):
            node_id = id(self.level2s[i])

            if node_id in processed:
                continue
            x_cursor += self.level2s[i].width(transpose) + 10
            # previous_level_height = self.level2s[i].height(transpose) # not used?
            processed.add(node_id)

            # keep packing while we're under the limit
            for j in range(i + 1, len(self.level2s)):
                node_id = id(self.level2s[j])
                if node_id in processed:
                    continue
                if x_cursor + self.level2s[j].width(transpose) <= DiagramConfig.MAX_PAGE_WIDTH['L1']:
                    x_cursor += self.level2s[j].width(transpose) + 10
            max_width = max(x_cursor, max_width)
            x_cursor = 0

        return max_width + 10

    def width(self, transpose=False):
        if EXPERIMENTAL:
            return self.width_new()

        result: int = self.horizontal_spacing
        if not transpose:
            for level2 in self.level2s:
                result += level2.dimensions(transpose=transpose)[1] + self.horizontal_spacing
        else:
            result += max(
                level2.dimensions(transpose=transpose)[1] for level2 in self.level2s) + self.horizontal_spacing
        return result

    def dimensions(self, transpose=False, **kwargs):
        if kwargs.get('tree'):
            return self.width(transpose=transpose), self.height(transpose=transpose)
        else:
            return self.width(transpose=transpose) * self.L0_SCALING, self.height(transpose=transpose) * self.L0_SCALING

    def widest_level2(self):
        return max(level2.width() for level2 in self.level2s)

    def __str__(self):
        return 'Leve1: %s %s %s' % (self.name, self.x, self.y)

    def appender(self, root, transpose=False, **kwargs):
        # TODO: not clear what the tree flag was used for, probably portrait/landscape mode, needs confirmation
        if (not self.placed) and (not kwargs.get('tree')):
            self.x = kwargs['x']
            self.y = kwargs['y']
            self.placed = True
        elif self.placed:
            return
        else:
            kwargs['tree'] = True

        self.level2s = sorted(self.level2s, key=lambda x: len(x.applications), reverse=True)

        style = DiagramConfig.get_style('L1')

        # Define the conditions for adjusting font size based on the length of the name and horizontal space
        # this is related to font size, but we haven't worked out the ratios, so hardcoded for now
        # TODO: cleanup and move to config
        # TODO: if parent is scaled then we should scale the child too, currently no flag on parent
        # conditions_one = {'stringLength': 9, 'softwareApplicationBoxes': 1}
        # conditions_two = {'stringLength': 18, 'softwareApplicationBoxes': 2}
        # conditions_three = {'stringLength': 16, 'softwareApplicationBoxes': 1}

        logger.debug(f"Level1: {self.name} {self.width()} {self.height()} {style}")

        condition_one = len(self.name) > 26 and self.width() == SoftwareApplication.width + 4 * self.horizontal_spacing
        condition_two = (len(self.name) > 26 and self.width() == 2 * SoftwareApplication.width + 5 *
                         self.horizontal_spacing)

        # lots of text, only one column
        condition_three = len(self.name) > 9 and self.width() == SoftwareApplication.width + 4 * self.horizontal_spacing

        if condition_one or condition_two:
            adjusted_font_size = utils.reduce_font_size(DiagramConfig.CONFIG['L1']['fontSize'], steps=2)
            style = ';'.join([f"fontSize={adjusted_font_size}" if 'fontSize=' in s else s for s in style.split(';')])
            # reduce font size for children too
            for level2 in self.level2s:
                level2.parent_reduced_font_size = True

        if condition_three:
            adjusted_font_size = utils.reduce_font_size(DiagramConfig.CONFIG['L1']['fontSize'], steps=2)
            style = ';'.join([f"fontSize={adjusted_font_size}" if 'fontSize=' in s else s for s in style.split(';')])



        width, height = self.dimensions(transpose=transpose, **kwargs)

        container = get_rectangle(parent=find_layer_id(root, 'Containers'),
                                  value=self.name,
                                  style=style,
                                  x=self.x,
                                  y=self.y,
                                  width=width,
                                  height=height)
        root.append(container)

        container = get_rectangle_link_overlay(parent=find_layer_id(root, 'LinkOverlay'),
                                               value="",
                                               link="/" + self.name.replace(" ", "+") + "+Detail",
                                               style='fillColor=none;strokeColor=none;',
                                               x=self.x,
                                               y=self.y,
                                               width=width,
                                               height=height)
        root.append(container)


        if kwargs['tree']:
            # This is a starting point for L2 diagrams
            L2_x_cursor = self.x + 10
            L2_y_cursor = self.y + self.header_height

            if not EXPERIMENTAL:
            # Last working code comment here ...
                if not transpose:
                    for level2 in self.level2s:
                        level2.x = L2_x_cursor
                        level2.y = L2_y_cursor
                        level2.appender(root)
                        L2_x_cursor += level2.width() + 10
                else:
                    for level2 in self.level2s:
                        level2.x = L2_x_cursor
                        level2.y = L2_y_cursor
                        level2.appender(root, transpose)
                        L2_y_cursor += level2.dimensions(transpose)[0] + 10
            else:
                for i in range(len(self.level2s)):
                    if not self.level2s[i].placed:
                        self.level2s[i].x = L2_x_cursor
                        self.level2s[i].y = L2_y_cursor
                        self.level2s[i].appender(root, transpose)
                        self.level2s[i].placed = True
                        L2_x_cursor += self.level2s[i].width(transpose) + 10
                        previous_level_height = self.level2s[i].height(transpose)
                        for j in range(i + 1, len(self.level2s)):
                            if not self.level2s[j].placed:
                                if L2_x_cursor + self.level2s[j].width(transpose) <= DiagramConfig.MAX_PAGE_WIDTH['L1']:
                                # We're under limit, keep adding until we reach MAX_PAGE_WIDTH
                                    self.level2s[j].x = L2_x_cursor
                                    self.level2s[j].y = L2_y_cursor
                                    self.level2s[j].appender(root, transpose)
                                    self.level2s[j].placed = True
                                    L2_x_cursor += self.level2s[j].width(transpose) + 10
                                    if self.level2s[j].height(transpose) > previous_level_height:
                                        previous_level_height = self.level2s[j].height(transpose)
                        L2_x_cursor = self.x + 10
                        L2_y_cursor += previous_level_height + 10



    def render_partial_views(self, file_name):
        mxGraphModel = get_diagram_root()
        root = mxGraphModel.find("root")
        append_default_layers(root)
        self.x = 0
        self.y = 0
        self.appender(root, transpose=True)
        xml_to_file(mxGraphModel, file_name + '_' + self.name + '.drawio')


class Level2:
    def __init__(self, name):
        self.name = name
        self.applications = []
        self.y = 0
        self.x = 0
        self.placed = False
        self.vertical_spacing = 10
        self.horizontal_spacing = 10
        self.vertical_elements = 0
        self.horizontal_elements = 0
        self.header_height = DiagramConfig.HEADER_HEIGHT['L2']
        self.parent_reduced_font_size = False

    def size(self):
        return len(self.applications)

    def append(self, app):
        self.applications.append(app)
        self.applications.sort()
        self.vertical_elements, self.horizontal_elements = get_layout_size(len(self.applications))

    def dimensions(self, transpose=False):
        if transpose:
            temp_x = self.horizontal_elements
            temp_y = self.vertical_elements
            return self.height(temp_x), self.width(temp_y)
        else:
            return self.height(), self.width()

    def height(self, transpose=False):
        result = self.header_height
        result += (self.vertical_elements * self.applications[0].height
                   + (self.vertical_elements - 1) * self.vertical_spacing)
        return result

    def width(self, transpose=False):
        result = 20  # borders
        result += self.horizontal_elements * self.applications[0].width + (
                self.horizontal_elements - 1) * self.horizontal_spacing
        return result

    def __str__(self):
        return 'Level2: %s %s %s' % (self.name, self.height, self.width)



    def placements(self, transpose=False):
        if transpose:
            return list(it.product(range(self.vertical_elements), range(self.horizontal_elements)))
        else:
            return list(it.product(range(self.horizontal_elements), range(self.vertical_elements)))

    def appender(self, root, transpose=False):
        height, width = self.dimensions(transpose)

        # TODO: MEDIUM - We're rendering in alphabetical order columns-wise, but rows-wise would be better or make it a param
        # TODO: LOW - If parent is scaled then we should scale the child too, currently no flag on parent
        # TODO: LOW - Maybe move to config?

        conditions = [
            {'length': 24, 'app_containers': 2, 'font_size_step_down': 1, 'spacing': 1},
            {'length': 22, 'app_containers': 1, 'font_size_step_down': 3, 'spacing': 1},
            {'length': 16, 'app_containers': 1, 'font_size_step_down': 3, 'spacing': 1},
        ]

        font_size = DiagramConfig.CONFIG['L2']['fontSize']
        spacing = 5

        for condition in conditions:
            if len(self.name) > condition['length'] and self.width() == SoftwareApplication.width + (
                    condition['app_containers'] + 1) * self.horizontal_spacing:
                font_size = utils.reduce_font_size(DiagramConfig.CONFIG['L2']['fontSize'],
                                                   steps=condition['font_size_step_down'])
                spacing = condition['spacing']
                break


        container = get_rectangle(parent=find_layer_id(root, 'Containers'),
                                  value=self.name,
                                  style='rounded=0;whiteSpace=wrap;html=1;fillColor=#f5f5f5;fontColor=#333333;strokeColor=none;verticalAlign=top;spacing='
                                       + str(spacing) + ';fontStyle=0;fontSize='
                                       + str(font_size) + ';fontFamily=Helvetica;'
                                       + 'whiteSpace=wrap;',
                                  x=self.x, y=self.y, width=width, height=height)
        root.append(container)

        # Header at the top, need to shift all containers down
        self.y += self.header_height - 20

        # Applications
        for i, app in enumerate(self.applications):
            app.x = self.x + 10 + self.placements(transpose)[i][0] * (app.width + 10)
            app.y = self.y + 10 + self.placements(transpose)[i][1] * (app.height + 10)
            app.appender(root)

    def render_partial_views(self, file_name, level1_name):
        mxGraphModel = get_diagram_root()
        root = mxGraphModel.find("root")
        append_default_layers(root)
        self.x = 0
        self.y = 0
        self.appender(root, transpose=True)
        xml_to_file(mxGraphModel, file_name + '_' + level1_name + '_' + self.name + '.drawio')

# class StyleBuilder:
#     @staticmethod
#     def get_style(**kwargs):
#         defaults = {
#             'style': 'rounded=1',
#             'whiteSpace': 'wrap',
#             'html': '1',
#             'fontFamily': 'Helvetica',
#             'fontStyle': '0',
#             'verticalAlign': 'middle',
#             'spacing': '0',
#             'arcSize': '4',
#             'spacingLeft': '2',
#             'spacingRight': '2',
#         }
#         defaults.update(kwargs)
#         return ';'.join(f'{key}={value}' for key, value in defaults.items())

class SWAppStyleBuilder:
    _instance = None
    _vertical_align = 'middle'  # Default value

    def __new__(cls, vertical_align=None):
        if cls._instance is None:
            cls._instance = super(SWAppStyleBuilder, cls).__new__(cls)
            if vertical_align is not None:
                cls._vertical_align = vertical_align
        return cls._instance

    @classmethod
    def set_vertical_align(cls, vertical_align):
        cls._vertical_align = vertical_align

    @classmethod
    def get_style(cls, **kwargs):
        defaults = {
            'style': 'rounded=1',
            'whiteSpace': 'wrap',
            'html': '1',
            'fontFamily': 'Helvetica',
            'fontStyle': '0',
            'verticalAlign': cls._vertical_align,  # Use the class variable
            'spacing': '0',
            'arcSize': '4',
            'spacingLeft': '2',
            'spacingRight': '2',
        }
        defaults.update(kwargs)
        return ';'.join(f'{key}={value}' for key, value in defaults.items())



class HostingPattern(Enum):
    AZURE = 'verticalLabelPosition=bottom;html=1;verticalAlign=top;align=center;strokeColor=none;fillColor=#00BEF2;shape=mxgraph.azure.azure_instance;fontFamily=Expert Sans Regular;aspect=fixed;'
    AWS = 'dashed=0;outlineConnect=0;html=1;align=center;labelPosition=center;verticalLabelPosition=bottom;verticalAlign=top;shape=mxgraph.webicons.amazon;gradientColor=#DFDEDE;strokeColor=#FFFFFF;strokeWidth=1;fontFamily=Expert Sans Regular;aspect=fixed;'
    LINUX = "pointerEvents=1;shadow=0;dashed=0;html=1;strokeColor=none;fillColor=#DF8C42;labelPosition=center;verticalLabelPosition=bottom;verticalAlign=top;align=center;outlineConnect=0;shape=mxgraph.veeam2.linux;fontFamily=Expert Sans Regular;aspect=fixed;"
    WINDOWS = "shadow=0;dashed=0;html=1;strokeColor=none;fillColor=#EF8F21;labelPosition=center;verticalLabelPosition=bottom;verticalAlign=top;align=center;outlineConnect=0;shape=mxgraph.veeam.ms_windows;fontFamily=Expert Sans Regular;"
    OPENSHIFT = "aspect=fixed;html=1;points=[];align=center;image;fontSize=12;image=img/lib/mscae/OpenShift.svg;strokeColor=#FFFFFF;strokeWidth=1;fillColor=#333333;"
    WINDOWSVM = "shadow=0;dashed=0;html=1;strokeColor=none;fillColor=#4495D1;labelPosition=center;verticalLabelPosition=bottom;verticalAlign=top;align=center;outlineConnect=0;shape=mxgraph.veeam.vm_windows;fontFamily=Expert Sans Regular;aspect=fixed;"

class SoftwareApplication:
    width = 160

    def __init__(self, name, **kwargs):
        self.name = name
        # self.name gains layout markup such as a leading <br>; keep the original for
        # anything a human reads.
        self.original_name = name
        self.height = 80 if DiagramConfig.SHOW_PICTOGRAMS else 50
        self.x = 0
        self.y = 0
        self.kwargs = kwargs
        self.style = ''
        self.show_pictograms = DiagramConfig.SHOW_PICTOGRAMS

    def column(self, name, default=None):
        """Read an optional CSV column.

        Every column but Level1, Level2 and AppName is optional, and pandas reports an
        empty cell as NaN, so absent and blank have to mean the same thing here.
        """
        value = self.kwargs.get(name, default)
        if value is None or value != value:  # NaN is the only value unequal to itself
            return default
        if isinstance(value, str) and not value.strip():
            return default
        return value

    def __lt__(self, other):
        return self.name < other.name

    def determine_font_size(self):
        if len(self.name) > 50:
            return utils.reduce_font_size(DiagramConfig.CONFIG['App']['fontSize'], steps=0)
        elif len(self.name) > 26:
            self.name = "<br>" + self.name
            return utils.reduce_font_size(DiagramConfig.CONFIG['App']['fontSize'], steps=0)
        return DiagramConfig.CONFIG['App']['fontSize']

    @staticmethod
    def get_style_for_hosting_pattern(hosting_pattern):
        return HostingPattern[hosting_pattern.upper()].value

    def appender(self, root):

        font_size = self.determine_font_size()

        if DiagramConfig.SHOW_PICTOGRAMS and not self.name.startswith("<br>"):
            self.name = "<br>" + self.name


        link = self.column('Link')
        if link:
            container = create_rectangle_with_optional_link(parent=find_layer_id(root, 'Applications'),
                                                            value=self.name,
                                                            style=swapp_style_builder.get_style(fontSize=font_size),
                                                            x=self.x, y=self.y, width=self.width, height=self.height,
                                                            link=link)
        else:
            container = create_rectangle_with_optional_link(parent=find_layer_id(root, 'Applications'),
                                                            value=self.name,
                                                            style=swapp_style_builder.get_style(fontSize=font_size),
                                                            x=self.x, y=self.y, width=self.width, height=self.height)
        root.append(container)

        if self.show_pictograms:
            # Controls
            controls = self.column('Controls')
            if controls:
                container = get_rectangle_link_overlay(parent=find_layer_id(root, 'Controls'), value=self.name,
                                                       style=swapp_style_builder.get_style(fontSize=font_size, fillColor='#f9f7ed',
                                                                                         strokeColor='#36393d;'),
                                                       x=self.x, y=self.y, width=self.width, height=self.height,
                                                       link=controls)
                root.append(container)
                # this is link on top of the Controls pictogram
                container = get_rectangle_link_overlay(parent=find_layer_id(root, 'Controls'), value="CON",
                                                       style="pointerEvents=1;shadow=0;dashed=0;strokeColor=none;fillColor=#505050;labelPosition=right;verticalLabelPosition=middle;verticalAlign=middle;outlineConnect=0;align=left;shape=mxgraph.office.security.lock_with_key_security_blue;aspect=fixed;fontFamily=Expert Sans Regular;fontSize=16;fontStyle=1",
                                                       x=self.x + 100, y=self.y + 52, width="22.69", height="28", link=controls)
                root.append(container)
            else:
                container = get_rectangle(parent=find_layer_id(root, 'Controls'),
                                          value=self.name,
                                          style=swapp_style_builder.get_style(fontSize=font_size),
                                          x=self.x, y=self.y, width=self.width, height=self.height)
                root.append(container)

        # StatusRAG - colour of the shole application on the Strategy layer

        status = self.column('StatusRAG')
        if status in DiagramConfig.STATUS_COLORS:
            self.style = swapp_style_builder.get_style(fontSize=font_size, **DiagramConfig.STATUS_COLORS[status])

        container = get_rectangle(parent=find_layer_id(root, 'Strategy'),
                                  value=self.name,
                                  style=self.style,
                                  x=self.x, y=self.y, width=self.width, height=self.height)
        root.append(container)

        # Resilience and Category are the same idea under two names; the bundled examples
        # use one each.
        resilience = self.column('Resilience', self.column('Category'))
        if resilience is not None:
            try:
                resilience = int(resilience)
            except (TypeError, ValueError):
                raise InvalidInput(
                    f"'{self.original_name}': resilience/category must be a number 0-4, "
                    f"got {resilience!r}")
            if resilience not in DiagramConfig.RESILIENCE_COLORS:
                raise InvalidInput(
                    f"'{self.original_name}': resilience/category must be 0-4, got {resilience}")
            self.style = swapp_style_builder.get_style(fontSize=font_size, **DiagramConfig.RESILIENCE_COLORS[resilience])

            container = get_rectangle(parent=find_layer_id(root, 'Resilience'), value=self.name,
                                      style=self.style,
                                      x=self.x, y=self.y, width=self.width, height=self.height)
            root.append(container)


        # TC - TC indicator
        container = get_rectangle(parent=find_layer_id(root, 'TransactionCycle'),
                                  value=str(self.column('TC', '')),
                                  style='text;html=1;'
                                        'strokeColor=none;'
                                        'fillColor=none;'
                                        'align=center;'
                                        'verticalAlign=middle;'
                                        'whiteSpace=wrap;'
                                        'rounded=0;'
                                        'labelBackgroundColor=none;'
                                        'fontFamily=Helvetica;'
                                        'fontStyle=1;'
                                        'fontSize=12;'
                                        'fontColor=#333333;',
                                  x=self.x,
                                  y=self.y,
                                  width=60,
                                  height=20)
        root.append(container)

        def get_date_color(date_str):
            given_date = datetime.strptime(date_str, "%Y-%m")
            current_year = datetime.now().year

            if given_date.year == current_year:
                return "FF3333"
            elif given_date.year > current_year:
                return "EC9706"
            else:
                logger.error(f"Date is in the past: {date_str}")
                return "326800"

        # Decomm Date
        decomm_date = self.column('DecommDate')
        if decomm_date is not None:
            container = get_rectangle(parent=find_layer_id(root, 'TransactionCycle'), value='Cease ' + str(decomm_date),
                                      style='text;html=1;strokeColor=none;fillColor=none;align=right;verticalAlign=middle;' +
                                            'whiteSpace=wrap;rounded=0;labelBackgroundColor=none;' +
                                            'fontFamily=Helvetica;fontStyle=1;fontSize=11;fontColor=#' +
                                            get_date_color(decomm_date) + ';',
                                      x=self.x + self.width - 80, y=self.y, width=80, height=20)
            root.append(container)


        if self.show_pictograms:
            # Harvey - Harvey ball
            angle = float(self.column('HostingPercent', 0)) / 100
            if angle == 1:
                container = get_rectangle(parent=find_layer_id(root, 'Hosting'), value='',
                                          style='ellipse;whiteSpace=wrap;html=1;aspect=fixed;strokeColor=none;fillColor=#333333;',
                                          x=self.x + 5, y=self.y + 52, width=25, height=25)
                root.append(container)
            elif angle != 0:
                container = get_rectangle(parent=find_layer_id(root, 'Hosting'), value='',
                                          style='verticalLabelPosition=bottom;verticalAlign=top;html=1;shape=mxgraph.basic.pie;startAngle=' + str(
                                                 1 - angle) + ';endAngle=1;strokeWidth=5;strokeColor=none;aspect=fixed;direction=east;fillColor=#333333;',
                                          x=self.x + 5, y=self.y + 52, width=25, height=25)
                root.append(container)

            # Hosting patterns
            for column, offset in (('HostingPattern1', 40), ('HostingPattern2', 68)):
                pattern = self.column(column)
                if pattern is None:
                    continue
                container = get_rectangle(parent=find_layer_id(root, 'Hosting'), value='',
                                          style=self.get_style_for_hosting_pattern(pattern),
                                          x=self.x + offset, y=self.y + 52, width=25, height=25)
                root.append(container)

            # Trend arrows
            for column, offset in (('Arrow1', 103), ('Arrow2', 130)):
                arrow = self.column(column)
                if arrow is None:
                    continue
                direction = "north" if arrow == 'up' else "south"
                container = get_rectangle(parent=find_layer_id(root, 'Metrics'), value='',
                                          style="html=1;shadow=0;dashed=0;align=center;verticalAlign=middle;"
                                                "shape=mxgraph.arrows2.arrow;dy=0.5;dx=13.86;direction=" + direction +
                                                ";notch=0;strokeColor=#FFFFFF;strokeWidth=1;fillColor=#333333;"
                                                "fontFamily=Expert Sans Regular;",
                                          x=self.x + offset, y=self.y + 52, width=25, height=25)
                root.append(container)


def get_diagram_root():
    mxGraphModel = etree.Element('mxGraphModel')
    mxGraphModel.set('dx', '981')
    mxGraphModel.set('dy', '650')
    mxGraphModel.set('grid', '1')
    mxGraphModel.set('gridSize', '10')
    mxGraphModel.set('guides', '1')
    mxGraphModel.set('tooltips', '1')
    mxGraphModel.set('connect', '1')
    mxGraphModel.set('arrows', '1')
    mxGraphModel.set('fold', '1')
    mxGraphModel.set('page', '1')
    mxGraphModel.set('pageScale', '1')
    mxGraphModel.set('pageWidth', '816')
    mxGraphModel.set('pageHeight', '1056')
    mxGraphModel.set('math', '0')
    mxGraphModel.set('shadow', '0')
    root = etree.Element('root')
    mxGraphModel.append(root)
    # top cell always there, layers inherit from it
    mxcell = etree.Element('mxCell')
    mxcell.set('id', '0')
    root.append(mxcell)
    # background layer, always there, we don't draw on it
    background = etree.Element('mxCell')
    background.set('id', '1')
    background.set('style', 'locked=1')
    background.set('parent', '0')
    background.set('visible', '0')
    root.append(background)
    return mxGraphModel

def create_layer(name):
    mxcell = etree.Element('mxCell')
    mxcell.set('id', get_random_id())
    mxcell.set('value', name)
    mxcell.set('style', 'locked=1')
    mxcell.set('parent', '0')
    return mxcell

def append_default_layers(root):
    # back to front order, lowest layer first
    layers = {'L0': create_layer('L0'), 'Containers': create_layer('Containers'),
              'Applications': create_layer('Applications'), 'Strategy': create_layer('Strategy'),
              'Controls': create_layer('Controls'), 'Resilience': create_layer('Resilience'),
              'Hosting': create_layer('Hosting'), 'Metrics': create_layer('Metrics'),
              'TransactionCycle': create_layer('TransactionCycle'), 'LinkOverlay': create_layer('LinkOverlay')}
    for layer in layers.values():
        root.append(layer)
    return root

def get_random_id(size=22, chars=string.ascii_uppercase + string.digits + string.ascii_lowercase + '-_'):
    # We could do something more deterministic here, but given it's 22 characters there's enough combinations
    # https://stackoverflow.com/questions/2257441/random-string-generation-with-upper-case-letters-and-digits
    return ''.join(random.choice(chars) for _ in range(size))

def get_layout_size(elements):
    layout_sizes = {
        1: (1, 1),
        2: (1, 2),
        3: (2, 2),
        4: (2, 2),
        5: (3, 2),
        6: (3, 2),
        7: (4, 2),
        8: (4, 2),
        9: (5, 2),
        10: (5, 2),
        11: (6, 2),
        12: (6, 2),
        13: (5, 3),
        range(14, 19): (6, 3),
        range(19, 25): (6, 4),
        range(25, 31): (6, 5),
        range(31, 36): (7, 5),
        range(36, 43): (7, 6),
        range(43, 50): (7, 7),
        range(50, 57): (7, 8),
        range(57, 64): (7, 9),
        range(64, 71): (7, 10),
        range(71, 78): (7, 11),
        range(78, 85): (7, 12),
        range(85, 92): (7, 13),
    }

    for key in layout_sizes:
        if isinstance(key, range) and elements in key:
            return layout_sizes[key]
        elif isinstance(key, int) and elements == key:
            return layout_sizes[key]

    if elements > 91:
        phi = (1 + math.sqrt(5)) / 2
        short_edge = math.floor((math.sqrt(elements * phi)) / phi)
        long_edge = math.ceil(elements / short_edge)
        return short_edge, long_edge

    raise ValueError(f'Unsupported number of elements: {elements}')


def xml_to_file(mxGraphModel, filename='output.drawio'):
    data = etree.tostring(mxGraphModel, pretty_print=False)
    data = drawio_tools.encode_diagram_data(data)
    root = etree.Element('mxfile')
    root.set('host', 'Electron')
    root.set('modified', '2022-05-01T08:12:20.636Z')
    root.set('agent',
             '5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) draw.io/14.5.1 Chrome/89.0.4389.82 Electron/12.0.1 Safari/537.36')
    root.set('etag', 'LL0dNY7hwAR5jEqHpxG4')
    root.set('version', '14.5.1')
    root.set('type', 'device')

    # another child with text
    child = etree.Element('diagram')
    child.set('id', 'nMbIOyWw1tff--0FTw4Q')
    child.set('name', 'Page-1')
    child.text = data
    root.append(child)

    # A relative name is resolved against ROOT_FOLDER; callers passing a path decide
    # for themselves.
    filepath = filename if os.path.isabs(filename) else os.path.join(ScriptConfig.ROOT_FOLDER, filename)
    tree = etree.ElementTree(root)
    logger.debug(f"Writing to file: {filepath}")
    tree.write(filepath)


def get_rectangle(parent, x, y, width, height, **kwargs):
    try:
        mxcell = etree.Element('mxCell')
        mxcell.set('id', get_random_id())
        mxcell.set('value', kwargs['value'])
        mxcell.set('style', kwargs['style'])
        mxcell.set('parent', parent)
        mxcell.set('vertex', '1')
        geometry = etree.Element('mxGeometry')
        geometry.set('x', str(x))
        geometry.set('y', str(y))
        geometry.set('width', str(width))
        geometry.set('height', str(height))
        geometry.set('as', 'geometry')
        mxcell.append(geometry)
        return mxcell
    except Exception as e:
        print(e)
        print(kwargs)
        RuntimeError('create_rectangle failed')


def get_rectangle_link_overlay(parent, x, y, width, height, **kwargs):
    try:
        UserObject = etree.Element('UserObject')
        UserObject.set('id', get_random_id())
        UserObject.set('link', kwargs['link'])
        UserObject.set('label', kwargs['value'])
        mxcell = etree.Element('mxCell')
        mxcell.set('id', get_random_id())
        mxcell.set('style', kwargs['style'])
        mxcell.set('parent', parent)
        mxcell.set('vertex', '1')
        geometry = etree.Element('mxGeometry')
        geometry.set('x', str(x))
        geometry.set('y', str(y))
        geometry.set('width', str(width))
        geometry.set('height', str(height))
        geometry.set('as', 'geometry')
        mxcell.append(geometry)
        UserObject.append(mxcell)
        return UserObject
    except Exception as e:
        print(e)
        print(kwargs)
        RuntimeError('create_linked_rectangle failed')

def create_rectangle_with_optional_link(parent, x, y, width, height, **kwargs):
    # Initialize the base mxCell element
    mxcell = etree.Element('mxCell')
    mxcell.set('id', get_random_id())
    mxcell.set('value', kwargs.get('value', ''))
    mxcell.set('style', kwargs.get('style', ''))
    mxcell.set('parent', parent)
    mxcell.set('vertex', '1')

    # Set the geometry
    geometry = etree.Element('mxGeometry')
    geometry.set('x', str(x))
    geometry.set('y', str(y))
    geometry.set('width', str(width))
    geometry.set('height', str(height))
    geometry.set('as', 'geometry')
    mxcell.append(geometry)

    # If a link is provided, wrap mxCell in a UserObject and set the link
    if 'link' in kwargs:
        UserObject = etree.Element('UserObject')
        UserObject.set('id', get_random_id())
        UserObject.set('link', kwargs['link'])
        UserObject.set('label', kwargs.get('value', ''))
        UserObject.append(mxcell)
        return UserObject
    else:
        return mxcell


def find_layer_id(root, name):
    for node in root.findall('.//mxCell[@parent="0"][@value="' + name + '"]'):
        return node.get('id')



def read_landscape_csv(file):
    """Read and validate a landscape CSV. Raises InvalidInput with a usable message."""
    try:
        df = pd.read_csv(file, quoting=csv.QUOTE_ALL)
    except FileNotFoundError:
        raise InvalidInput(f"no such file: {file}")
    except Exception as exc:
        raise InvalidInput(f"could not read {file}: {exc}")

    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise InvalidInput(
            f"{file} is missing required column(s): {', '.join(missing)}. "
            f"Required: {', '.join(REQUIRED_COLUMNS)}.")

    if df.empty:
        raise InvalidInput(f"{file} has no rows")

    ignored = [column for column in df.columns
               if column not in REQUIRED_COLUMNS and column not in OPTIONAL_COLUMNS]
    if ignored:
        logger.warning("Ignoring column(s) the renderer does not use: %s", ', '.join(ignored))

    return df


def render_L1(file, output=None, partial_views=False):
    # mxGraphModel is the true "root" of the graph
    mxGraphModel = get_diagram_root()
    root = mxGraphModel.find("root")
    append_default_layers(root)

    df = read_landscape_csv(file)

    # build the structure
    level1s = []
    for index, app in df.iterrows():
        # check if we already have L1 object and if not create it otherwise reference it
        L1 = next((x for x in level1s if x.name == app['Level1']), None)

        if not L1:
            L1 = Level1(app['Level1'])
            level1s.append(L1)

        # check if we already have L2 object (as child of L1)
        L2 = next((x for x in L1.level2s if x.name == app['Level2']), None)

        if not L2:
            L2 = Level2(app['Level2'])
            L1.level2s.append(L2)

        # Not expecting any apps with the same name at the leaf level
        if any(sa.original_name == app['AppName'] for sa in L2.applications):
            raise InvalidInput(
                f"row {index + 2}: '{app['AppName']}' appears twice under "
                f"{app['Level1']} / {app['Level2']}; application names must be unique "
                f"within a level 2 grouping")

        # Take the remaining columns apart from Level1 and Level2 and create the SoftwareApplication out of it
        # Load this dynamically from the dataframe
        software_app_kwargs = {col: app[col] for col in df.columns if col not in ['Level1', 'Level2']}
        L2.append(SoftwareApplication(app['AppName'], **software_app_kwargs))

        #L2.append(SoftwareApplication(app['AppName'], TC=app['TC'], StatusRAG=app['StatusRAG'], Status=app['Status']
        #                              , HostingPercent=app['HostingPercent'], HostingPattern1=app['HostingPattern1'],
        #                              HostingPattern2=app['HostingPattern2'], Arrow1=app['Arrow1'],
        #                              Arrow2=app['Arrow2'], Link=app['Link'], Controls=app['Controls'],
        #                              DecommDate=app['DecommDate']))

    level1s = sorted(level1s, key=lambda x: x.width(), reverse=True)



    # Commented out as we do want to limit width for print (as opposed to leave it wide for web)
    #if level1s[0].width() > MAX_PAGE_WIDTH:
    #    MAX_PAGE_WIDTH = level1s[0].width()

    L1_x_cursor = 0
    L1_y_cursor = 0

    for i in range(len(level1s)):
        if not level1s[i].placed:
            level1s[i].x = L1_x_cursor
            level1s[i].y = L1_y_cursor
            level1s[i].appender(root, tree=True)
            level1s[i].placed = True
            L1_x_cursor += level1s[i].width() + 10
            previous_level_height = level1s[i].height()
            for j in range(i + 1, len(level1s)):
                if not level1s[j].placed:
                    if L1_x_cursor + level1s[j].width() <= MAX_PAGE_WIDTH:
                        level1s[j].x = L1_x_cursor
                        level1s[j].y = L1_y_cursor
                        level1s[j].appender(root, tree=True)
                        level1s[j].placed = True
                        L1_x_cursor += level1s[j].width() + 10
                        if level1s[j].height() > previous_level_height:
                            previous_level_height = level1s[j].height()
            L1_x_cursor = 0
            L1_y_cursor += previous_level_height + 10

    # Output sits next to the input unless told otherwise.
    if output is None:
        output = os.path.splitext(file)[0] + '.drawio'
    output = os.path.abspath(output)

    logger.info(f"Writing {output}")
    xml_to_file(mxGraphModel, output)

    if DEBUG:
        drawio_shared_functions.pretty_print(mxGraphModel)

    if partial_views:
        render_partial_views(os.path.splitext(output)[0], level1s)

    if ScriptConfig.OPEN_IN_DRAWIO:
        os.system(f'"{ScriptConfig.DRAWIO_EXECUTABLE}" "{output}"')

    return output

def render_partial_views(file_name, level1s):
    for level1 in level1s:
        level1.render_partial_views(file_name)
        for level2 in level1.level2s:
            level2.render_partial_views(file_name, level1.name)


def main(file, output=None, partial_views=False):
    """Render a landscape diagram from a CSV. Returns the path written."""
    global swapp_style_builder
    if DiagramConfig.SHOW_PICTOGRAMS:
        swapp_style_builder = SWAppStyleBuilder(vertical_align='top')
    else:
        swapp_style_builder = SWAppStyleBuilder(vertical_align='middle')

    return render_L1(file, output=output, partial_views=partial_views)


# L0 would add a further level of aggregation above L1. It is not supported: the
# renderer was never finished and no example data carries the extra level.


if __name__ == "__main__":
    from drawio_application_landscape.cli import main as cli_main

    sys.exit(cli_main())
