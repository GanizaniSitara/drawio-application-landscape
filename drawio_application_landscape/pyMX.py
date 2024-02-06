import logging

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
import drawio_shared_functions
import drawio_tools

from drawio_application_landscape.config import DiagramConfig
import utils



class Level0:
    def __init__(self, name):
        self.name = name
        self.level1s = []
        self.placed = False
        self.x = 0
        self.y = 0
        self.max_L0_width = 1800
        self.TITLE_SPACING = 70
        self.L0_SCALING = 0.5

    def append(self, app):
        self.level1s.append(app)
        self.level1s = sorted(self.level1s, key=lambda x: x.size(), reverse=True)

    def width(self):
        return 10 + sum(level1.dimensions(tree=False)[0] + 10 for level1 in self.level1s)

    # def height(self):
    #     return self.TITLE_SPACING + (level1.height() for level1 in self.level1s)

    def size(self):
        # print(f"Level0: {self.name} {len(self.level1s)} {size} {self.width()} {self.height()}")
        return sum([x.size() for x in self.level1s])

    def appender(self, root, transpose=False, **kwargs):
        self.x = kwargs['x'] if kwargs['x'] != self.x else self.x
        self.y = kwargs['y'] if kwargs['y'] != self.y else self.y

        L1_x = self.x
        L1_y = self.y
        L1_x_cursor = L1_x + 10
        L1_y_cursor = L1_y + self.TITLE_SPACING
        previous_level_height = 0

        for i in range(len(self.level1s)):
            if not self.level1s[i].placed:
                self.level1s[i].appender(root, x=L1_x_cursor, y=L1_y_cursor, tree=False)
                L1_x_cursor += self.level1s[i].width(transpose=False, tree=False) * self.L0_SCALING  + 10
                if self.level1s[i].height(tree=False) > previous_level_height:
                    previous_level_height = self.level1s[i].height(tree=False) * self.L0_SCALING
                for j in range(i + 1, len(self.level1s)):
                    if not self.level1s[j].placed:
                        if L1_x_cursor + self.level1s[j].width(transpose=False, tree=False) <= self.max_L0_width:
                            self.level1s[j].appender(root, x=L1_x_cursor, y=L1_y_cursor, tree=False)
                            L1_x_cursor += self.level1s[j].width(transpose=False, tree=False) * self.L0_SCALING + 10
                            if self.level1s[j].height(tree=False) > previous_level_height:
                                previous_level_height = self.level1s[i].height(tree=False) * self.L0_SCALING
                L1_x_cursor = 0
                L1_y_cursor += previous_level_height + 10

        self.height = L1_y_cursor - L1_y

        container = get_rectangle(parent=find_layer_id(root, 'L0'), value=self.name,
                                  style=';whiteSpace=wrap;html=1;fontFamily=Expert Sans Regular;fontSize='
                                           + '48'
                                           + ';fontColor=#333333;strokeColor=none;fillColor=#888888;verticalAlign=top;spacing='
                                           + '2' + ';fontStyle=0',
                                  x=L1_x, y=L1_y, width=self.width(), height=self.height)
        root.append(container)

        # for level1 in self.level1s:
        #     level1.appender(root, x=self.x, y=self.y, tree=False)


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

    # def number_of_elements(self):
    #     return self.vertical * self.horizontal

    def size(self):
        return sum([level2.size() for level2 in self.level2s])

    def height(self, transpose=False, **kwargs):
        result = self.header_height
        if not transpose:
            result += max(level2.dimensions(transpose=transpose)[0] for level2 in self.level2s) + self.vertical_spacing
        else:
            for level2 in self.level2s:
                result += level2.dimensions(transpose=transpose)[0] + self.vertical_spacing
        return result

    def width(self, transpose=False, **kwargs):
        ret_val = self.horizontal_spacing
        if not transpose:
            for level2 in self.level2s:
                ret_val += level2.dimensions(transpose=transpose)[1] + self.horizontal_spacing
        else:
            ret_val += max(
                level2.dimensions(transpose=transpose)[1] for level2 in self.level2s) + self.horizontal_spacing
        return ret_val

    def dimensions(self, transpose=False, **kwargs):
        if kwargs.get('tree'):
            return self.width(transpose=transpose), self.height(transpose=transpose)
        else:
            return self.width(transpose=transpose) * self.L0_SCALING, self.height(transpose=transpose) * self.L0_SCALING

    def widest_level2(self):
        return max(level2.width() for level2 in self.level2s)

    def __str__(self):
        return 'Leve1: %s %s %s %s' % (self.name, self.vertical, self.horizontal)

    def appender(self, root, transpose=False, **kwargs):
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
        conditions_one = {'stringLenght': 9, 'softwareApplicationBoxes': 1}
        conditions_two = {'stringLenght': 18, 'softwareApplicationBoxes': 2}
        scaling_ratio = 2 / 3
        logger.info(f"Level1: {self.name} {self.width()} {self.height()} {style}")
        condition_one = len(self.name) > 9 and self.width() == SoftwareApplication.width + 4 * self.horizontal_spacing
        condition_two = len(self.name) > 18 and self.width() == 2 * SoftwareApplication.width + 5 * self.horizontal_spacing

        if condition_one or condition_two:
            adjusted_font_size = utils.reduce_font_size(DiagramConfig.CONFIG['L1']['fontSize'])
            style = ';'.join([f"fontSize={adjusted_font_size}" if 'fontSize=' in s else s for s in style.split(';')])
            # reduce font size for children too
            for level2 in self.level2s:
                level2.parent_reduced_font_size = True

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
                                               link="/" + (self.name).replace(" ", "+") + "+Detail",
                                               style='fillColor=none;strokeColor=none;',
                                               x=self.x,
                                               y=self.y,
                                               width=width,
                                               height=height)
        root.append(container)

        if kwargs['tree']:
            L2_x_cursor = self.x + 10
            L2_y_cursor = self.y + self.header_height

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
        self.vertical_elements, self.horizontal_elements = get_layout_size(len(self.applications))

    def dimensions(self, transpose=False):
        if transpose:
            temp_x = self.horizontal_elements
            temp_y = self.vertical_elements
            return self.height(temp_x), self.width(temp_y)
        else:
            return self.height(), self.width()

    def height(self, vertical_elements=None):
        if vertical_elements is None:
            vertical_elements = self.vertical_elements
        result = self.header_height
        result += (vertical_elements * self.applications[0].height
                   + (vertical_elements - 1) * self.vertical_spacing)
        return result

    def width(self, horizontal_elements=None):
        if horizontal_elements is None:
            horizontal_elements = self.horizontal_elements
        # self.vertical_elements, self.horizontal_elements = get_layout_size(len(self.applications))
        result = 20  # borders
        result += horizontal_elements * self.applications[0].width + (
                horizontal_elements - 1) * self.horizontal_spacing
        return result

    def __str__(self):
        return 'Level2: %s %s %s %s' % (self.level1, self.level2, self.height, self.width)

    def placements(self, transpose=False):
        if transpose:
            return list(it.product(range(self.vertical_elements), range(self.horizontal_elements)))
        else:
            return list(it.product(range(self.horizontal_elements), range(self.vertical_elements)))

    def appender(self, root, transpose=False):
        height, width = self.dimensions(transpose)

        # Define the conditions for adjusting font size based on the length of the name and horizontal space
        # this is related to font size, but we haven't worked out the ratios, so hardcoded for now
        # TODO: cleanup and move to config
        # TODO: if parent is scaled then we should scale the child too, currently no flag on parent
        # TODO: also looks ugly both as code and in the diagram, we might not even need two different conditions
        # depending on the text size
        case_one = {'length': 16, 'app_containers': 1}
        case_two = {'length': 24, 'app_containers': 2}
        condition_one = (len(self.name) > case_one['length']
                         and
                         self.width() == SoftwareApplication.width + (case_one['app_containers'] + 1)
                            * self.horizontal_spacing)
        condition_two = (len(self.name) > case_two['length']
                         and self.width() == case_two['app_containers']
                            * SoftwareApplication.width + (case_two['app_containers'] + 1) * self.horizontal_spacing)

        if condition_one:
            # TODO: move to config and just use style builder
            font_size = utils.reduce_font_size(DiagramConfig.CONFIG['L2']['fontSize'],steps=3)
            spacing = 1
            # adjusted_font_size = utils.reduce_font_size(DiagramConfig.CONFIG['L2']['fontSize'])
            # style = ';'.join([f"fontSize={adjusted_font_size}" if 'fontSize=' in s else s for s in style.split(';')])
        elif condition_two:
            font_size = utils.reduce_font_size(DiagramConfig.CONFIG['L2']['fontSize'])
            spacing = 1
        else:
            font_size = DiagramConfig.CONFIG['L2']['fontSize']
            spacing = 5

        container = get_rectangle(parent=find_layer_id(root, 'Containers'),
                                  value=self.name,
                                  style='rounded=0;whiteSpace=wrap;html=1;fillColor=#f5f5f5;fontColor=#333333;strokeColor=none;verticalAlign=top;spacing='
                                           + str(spacing) + ';fontStyle=0;fontSize='
                                           + str(font_size) + ';fontFamily=Helvetica;',
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


class SoftwareApplication:
    width = 160

    def __init__(self, name, **kwargs):
        self.name = name
        self.height = 80
        self.x = 0
        self.y = 0
        self.kwargs = kwargs
        self.style = ''
        self.show_pictograms = DiagramConfig.SHOW_PICTOGRAMS

        if self.show_pictograms:
            self.height = 80
        else:
            self.height = 50



    def get_style_for_hosting_pattern(self, hosting_pattern):
        if hosting_pattern == 'Azure':
            style = 'verticalLabelPosition=bottom;html=1;verticalAlign=top;align=center;strokeColor=none;fillColor=#00BEF2;shape=mxgraph.azure.azure_instance;fontFamily=Expert Sans Regular;aspect=fixed;'
        elif hosting_pattern == 'AWS':
            style = 'dashed=0;outlineConnect=0;html=1;align=center;labelPosition=center;verticalLabelPosition=bottom;verticalAlign=top;shape=mxgraph.webicons.amazon;gradientColor=#DFDEDE;strokeColor=#FFFFFF;strokeWidth=1;fontFamily=Expert Sans Regular;aspect=fixed;'
        elif hosting_pattern == 'Linux':
            style = "pointerEvents=1;shadow=0;dashed=0;html=1;strokeColor=none;fillColor=#DF8C42;labelPosition=center;verticalLabelPosition=bottom;verticalAlign=top;align=center;outlineConnect=0;shape=mxgraph.veeam2.linux;fontFamily=Expert Sans Regular;aspect=fixed;"
        elif hosting_pattern == 'Windows':
            style = "shadow=0;dashed=0;html=1;strokeColor=none;fillColor=#EF8F21;labelPosition=center;verticalLabelPosition=bottom;verticalAlign=top;align=center;outlineConnect=0;shape=mxgraph.veeam.ms_windows;fontFamily=Expert Sans Regular;"
        elif hosting_pattern == 'OpenShift':
            style = "aspect=fixed;html=1;points=[];align=center;image;fontSize=12;image=img/lib/mscae/OpenShift.svg;strokeColor=#FFFFFF;strokeWidth=1;fillColor=#333333;"
        elif hosting_pattern == 'WindowsVM':
            style = "shadow=0;dashed=0;html=1;strokeColor=none;fillColor=#4495D1;labelPosition=center;verticalLabelPosition=bottom;verticalAlign=top;align=center;outlineConnect=0;shape=mxgraph.veeam.vm_windows;fontFamily=Expert Sans Regular;aspect=fixed;"
        return style

    def appender(self, root):
        if self.kwargs['Link']:
            container = get_rectangle_link_overlay(parent=find_layer_id(root, 'Applications'), value=self.name,
                                                   style='rounded=1;whiteSpace=wrap;html=1;fontFamily=Expert Sans Regular;fontSize=14;fontStyle=0;verticalAlign=top;spacing=10;arcSize=4;',
                                                   x=self.x, y=self.y, width=self.width, height=self.height,
                                                   link=self.kwargs['Link'])
        else:
            container = get_rectangle(parent=find_layer_id(root, 'Applications'), value=self.name,
                                      style='rounded=1;whiteSpace=wrap;html=1;fontFamily=Expert Sans Regular;fontSize=14;fontStyle=0;verticalAlign=top;spacing=10;arcSize=4;',
                                      x=self.x, y=self.y, width=self.width, height=self.height)
        root.append(container)


        if self.show_pictograms:
            # Controls
            if not (self.kwargs['Controls'] != self.kwargs['Controls']): # using pandas, returns NaN if empty
                container = get_rectangle_link_overlay(parent=find_layer_id(root, 'Controls'), value=self.name,
                                                       style='rounded=1;whiteSpace=wrap;html=1;fontFamily=Expert Sans Regular;fontSize=14;fontStyle=0;verticalAlign=top;spacing=11;arcSize=4;fillColor=#f9f7ed;strokeColor=#36393d;',
                                                       x=self.x, y=self.y, width=self.width, height=self.height,
                                                       link=self.kwargs['Controls'])
                root.append(container)
                container = get_rectangle_link_overlay(parent=find_layer_id(root, 'Controls'), value="CON",
                                                       style="pointerEvents=1;shadow=0;dashed=0;strokeColor=none;fillColor=#505050;labelPosition=right;verticalLabelPosition=middle;verticalAlign=middle;outlineConnect=0;align=left;shape=mxgraph.office.security.lock_with_key_security_blue;aspect=fixed;fontFamily=Expert Sans Regular;fontSize=16;fontStyle=1",
                                                       x=self.x + 100, y=self.y + 52, width="22.69", height="28", link=self.kwargs['Controls'])
                root.append(container)
            else:
                container = get_rectangle(parent=find_layer_id(root, 'Controls'), value=self.name,
                                          style='rounded=1;whiteSpace=wrap;html=1;fontFamily=Expert Sans Regular;fontSize=14;fontStyle=0;verticalAlign=top;spacing=10;arcSize=4;',
                                          x=self.x, y=self.y, width=self.width, height=self.height)
                root.append(container)


        # StatusRAG - colour of the shole application on the Strategy layer
        if self.kwargs['StatusRAG'] == 'red':
            self.style = 'rounded=1;whiteSpace=wrap;html=1;fontFamily=Expert Sans Regular;fontSize=14;fontStyle=0;verticalAlign=top;spacing=11;arcSize=4;fillColor=#F8CECC;strokeColor=#b85450;'
        elif self.kwargs['StatusRAG'] == 'amber':
            self.style = 'rounded=1;whiteSpace=wrap;html=1;fontFamily=Expert Sans Regular;fontSize=14;fontStyle=0;verticalAlign=top;spacing=11;arcSize=4;fillColor=#fff2cc;strokeColor=#d6b656;'
        elif self.kwargs['StatusRAG'] == 'green':
            self.style = 'rounded=1;whiteSpace=wrap;html=1;fontFamily=Expert Sans Regular;fontSize=14;fontStyle=0;verticalAlign=top;spacing=11;arcSize=4;fillColor=#D5E8D4;strokeColor=#82b366;'
        container = get_rectangle(parent=find_layer_id(root, 'Strategy'), value=self.name,
                                  style=self.style,
                                  x=self.x, y=self.y, width=self.width, height=self.height)
        root.append(container)

        # Resilience - colour of the resilience indicator
        if self.kwargs['Resilience'] == 0:
            self.style = 'rounded=1;whiteSpace=wrap;html=1;fontFamily=Expert Sans Regular;fontSize=14;fontStyle=0;verticalAlign=top;spacing=11;arcSize=4;fillColor=#fbc5cc;strokeColor=#10739e;'
        elif self.kwargs['Resilience'] == 1:
            self.style = 'rounded=1;whiteSpace=wrap;html=1;fontFamily=Expert Sans Regular;fontSize=14;fontStyle=0;verticalAlign=top;spacing=11;arcSize=4;fillColor=#f0bcc7;strokeColor=#10739e;'
        elif self.kwargs['Resilience'] == 2:
            self.style = 'rounded=1;whiteSpace=wrap;html=1;fontFamily=Expert Sans Regular;fontSize=14;fontStyle=0;verticalAlign=top;spacing=11;arcSize=4;fillColor=#b1ddf0;strokeColor=#10739e;'
        elif self.kwargs['Resilience'] == 3:
            self.style = 'rounded=1;whiteSpace=wrap;html=1;fontFamily=Expert Sans Regular;fontSize=14;fontStyle=0;verticalAlign=top;spacing=11;arcSize=4;fillColor=#f9f7ed;strokeColor=#36393d;'
        elif self.kwargs['Resilience'] == 4:
            self.style = 'rounded=1;whiteSpace=wrap;html=1;fontFamily=Expert Sans Regular;fontSize=14;fontStyle=0;verticalAlign=top;spacing=11;arcSize=4;fillColor=#dae8fc;strokeColor=#6c8ebf;'
        else:
            raise Exception (f"Resilience value not in range 0-4 for {self.name} {self.kwargs['Resilience']}")
        container = get_rectangle(parent=find_layer_id(root, 'Resilience'), value=self.name,
                                  style=self.style,
                                  x=self.x, y=self.y, width=self.width, height=self.height)
        root.append(container)

        # TC - TC indicator
        container = get_rectangle(parent=find_layer_id(root, 'TransactionCycle'), value=str(self.kwargs['TC']),
                                  style='text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;whiteSpace=wrap;rounded=0;labelBackgroundColor=none;fontFamily=Helvetica;fontStyle=1;fontSize=14;fontColor=#333333;',
                                  x=self.x + 1, y=self.y + 1, width=30, height=20)
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
        if not pd.isna(self.kwargs['DecommDate']):
            container = get_rectangle(parent=find_layer_id(root, 'TransactionCycle'), value='Cease ' + str(self.kwargs['DecommDate']),
                                      style='text;html=1;strokeColor=none;fillColor=none;align=right;verticalAlign=middle;' +
                                            'whiteSpace=wrap;rounded=0;labelBackgroundColor=none;' +
                                            'fontFamily=Helvetica;fontStyle=1;fontSize=11;fontColor=#' +
                                            get_date_color(self.kwargs['DecommDate']) + ';',
                                      x=self.x + self.width - 80, y=self.y, width=80, height=20)
            root.append(container)


        if self.show_pictograms:
            # Harvey - Harvey ball
            angle = self.kwargs['HostingPercent'] / 100
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

            # HostingPattern1
            container = get_rectangle(parent=find_layer_id(root, 'Hosting'), value='',
                                      style=self.get_style_for_hosting_pattern(self.kwargs['HostingPattern1']),
                                      x=self.x + 40, y=self.y + 52, width=25, height=25)
            root.append(container)

            # Hosting Pattern2
            container = get_rectangle(parent=find_layer_id(root, 'Hosting'), value='',
                                      style=self.get_style_for_hosting_pattern(self.kwargs['HostingPattern2']),
                                      x=self.x + 68, y=self.y + 52, width=25, height=25)
            root.append(container)

            # Arrow1
            container = get_rectangle(parent=find_layer_id(root, 'Metrics'), value='',
                                      style="html=1;shadow=0;dashed=0;align=center;verticalAlign=middle;shape=mxgraph.arrows2.arrow;dy=0.5;dx=13.86;direction=" + (
                                             "north" if self.kwargs[
                                                            'Arrow1'] == 'up' else "south") + ";notch=0;strokeColor=#FFFFFF;strokeWidth=1;fillColor=#333333;fontFamily=Expert Sans Regular;",
                                      x=self.x + 103, y=self.y + 52, width=25, height=25)
            root.append(container)

            # Arrow2
            container = get_rectangle(parent=find_layer_id(root, 'Metrics'), value='',
                                      style="html=1;shadow=0;dashed=0;align=center;verticalAlign=middle;shape=mxgraph.arrows2.arrow;dy=0.5;dx=13.86;direction=" + (
                                             "north" if self.kwargs[
                                                            'Arrow2'] == 'up' else "south") + ";notch=0;strokeColor=#FFFFFF;strokeWidth=1;fillColor=#333333;fontFamily=Expert Sans Regular;",
                                      x=self.x + 130, y=self.y + 52, width=25, height=25)
            root.append(container)

            # Metric
            #(self.x + self.y)
            container = get_rectangle(parent=find_layer_id(root, 'Metrics'), value='',
                                      style="html=1;shadow=0;dashed=0;align=center;verticalAlign=middle;shape=mxgraph.arrows2.arrow;dy=0.5;dx=13.86;direction=" + (
                                             "north" if self.kwargs[
                                                            'Arrow2'] == 'up' else "south") + ";notch=0;strokeColor=#FFFFFF;strokeWidth=1;fillColor=#333333;fontFamily=Expert Sans Regular;",
                                      x=self.x + 130, y=self.y + 52, width=25, height=25)
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
    layers = {}
    layers['L0'] = create_layer('L0')
    layers['Containers'] = create_layer('Containers')
    layers['Applications'] = create_layer('Applications')
    layers['Strategy'] = create_layer('Strategy')
    layers['Controls'] = create_layer('Controls')
    layers['Resilience'] = create_layer('Resilience')
    layers['Hosting'] = create_layer('Hosting')
    layers['Metrics'] = create_layer('Metrics')
    layers['TransactionCycle'] = create_layer('TransactionCycle')
    layers['LinkOverlay'] = create_layer('LinkOverlay')
    for layer in layers.values():
        root.append(layer)
    return root



# https://stackoverflow.com/questions/2257441/random-string-generation-with-upper-case-letters-and-digits
def get_random_id(size=22, chars=string.ascii_uppercase + string.digits + string.ascii_lowercase + '-_'):
    return ''.join(random.choice(chars) for _ in range(size))


# from number of elements return number of columns and rows needed for landscape layout
# this was generated by GitHub Copilot just from the comment above
# first error was made count 36 where 7x5 was suggested
# golden rectangle added manually for elements > 91
def get_layout_size(elements):
    if elements <= 1:
        return 1, 1
    elif elements == 2:
        return 2, 1
    elif elements == 3:
        return 3, 1
    elif elements == 4:
        return 4, 1
    elif elements == 5:
        return 5, 1
    elif elements == 6:
        return 6, 1
    elif elements == 7:
        return 4, 2
    elif elements == 8:
        return 4, 2
    elif elements == 9:
        return 5, 2
    elif elements == 10:
        return 5, 2
    elif elements == 11:
        return 6, 2
    elif elements == 12:
        return 6, 2
    elif elements in range(13, 19):
        return 6, 3
    elif elements in range(19, 25):
        return 6, 4
    elif elements in range(25, 31):
        return 6, 5
    elif elements in range(31, 36):
        return 7, 5
    elif elements in range(36, 43):
        return 7, 6
    elif elements in range(43, 50):
        return 7, 7
    elif elements in range(50, 57):
        return 7, 8
    elif elements in range(57, 64):
        return 7, 9
    elif elements in range(64, 71):
        return 7, 10
    elif elements in range(71, 78):
        return 7, 11
    elif elements in range(78, 85):
        return 7, 12
    elif elements in range(85, 92):
        return 7, 13
    elif elements > 91:
        phi = (1 + math.sqrt(5)) / 2
        short_edge = math.floor((math.sqrt(elements * phi)) / phi)
        long_edge = math.ceil(elements / short_edge)
        return short_edge, long_edge
    else:
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

    tree = etree.ElementTree(root)
    tree.write(filename)


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


def find_layer_id(root, name):
    for node in root.findall('.//mxCell[@parent="0"][@value="' + name + '"]'):
        return node.get('id')


def render_L0(file):
    try:
        df = pd.read_csv(file, quoting=csv.QUOTE_ALL, delim_whitespace=False)
    except Exception as e:
        print(e)
        print(f"Issue with file {file}")
        return
    level0s = []
    for index, row in df.iterrows():
        L0 = next((x for x in level0s if x.name == row['Level0']), None)
        if L0 is None:
            L0 = Level0(row['Level0'])
            level0s.append(L0)
        L1 = next((x for x in L0.level1s if x.name == row['Level1']), None)
        if L1 is None:
            L1 = Level1(row['Level1'])
            L0.append(L1)
        L2 = next((x for x in L1.level2s if x.name == row['Level2']), None)
        if L2 is None:
            L2 = Level2(row['Level2'])
            L1.level2s.append(L2)
        L2.append(SoftwareApplication(row['AppName']))

    for level0 in level0s:
        level0.size()


    mxGraphModel = get_diagram_root()
    root = mxGraphModel.find("root")
    append_default_layers(root)

    MAX_PAGE_WIDTH = DiagramConfig.MAX_PAGE_WIDTH['L0']

    L0_x_cursor = 0
    L0_y_cursor = 0

    for i in range(len(level0s)):
        if not level0s[i].placed:
            level0s[i].appender(root,x=L0_x_cursor,y=L0_y_cursor)
            level0s[i].placed = True
            L0_x_cursor += level0s[i].width() + 10
            previous_level_height = level0s[i].height
            for j in range(i + 1, len(level0s)):
                if not level0s[j].placed:
                    if L0_x_cursor + level0s[j].width() <= MAX_PAGE_WIDTH:
                        level0s[j].appender(root,x=L0_x_cursor,y=L0_y_cursor)
                        level0s[j].placed = True
                        L0_x_cursor += level0s[j].width() + 10
                        if level0s[j].height() > previous_level_height:
                            previous_level_height = level0s[j].height
            L0_x_cursor = 0
            L0_y_cursor += previous_level_height + 10

    xml_to_file(mxGraphModel, file[:-4] + '.drawio')

    drawio_shared_functions.pretty_print(mxGraphModel)

    os.system('"C:\Program Files\draw.io\draw.io.exe" ' + file[:-4] + ".drawio")


def render_L1(file):
    # mxGraphModel is the true "root" of the graph
    mxGraphModel = get_diagram_root()
    root = mxGraphModel.find("root")
    append_default_layers(root)

    try:
        df = pd.read_csv(file, quoting=csv.QUOTE_ALL, delim_whitespace=False)
    except Exception as e:
        print(e)
        print(f"Issue reading:{file}")
        return

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
        assert not any(sa.name == app['AppName'] for sa in L2.applications), f"Duplicate App with same parent - {app['AppName']}"

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

    MAX_PAGE_WIDTH = DiagramConfig.MAX_PAGE_WIDTH['L1']

    if level1s[0].width() > MAX_PAGE_WIDTH:
        MAX_PAGE_WIDTH = level1s[0].width()

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

    file_name = file[:-4]

    xml_to_file(mxGraphModel, file_name + '.drawio')

    drawio_shared_functions.pretty_print(mxGraphModel)
    os.system('"C:\Program Files\draw.io\draw.io.exe" ' + file_name + ".drawio")


def render_partial_views(file_name, level1s):
    for level1 in level1s:
        level1.render_partial_views(file_name)
        for level2 in level1.level2s:
            level2.render_partial_views(file_name, level1.name)


def main(render,file):
    if render == 'L1':
        render_L1(file)
    elif render == 'L0':
        render_L0(file)


if __name__ == "__main__":

    if sys.stdin and sys.stdin.isatty():
        print("Running interactively")
        main(sys.argv[1])
    elif sys.gettrace():
        print("Running in debugger")
        DEBUG = True
        loglevel = logging.basicConfig(level=logging.DEBUG,
                                       format='%(asctime)s.%(msecs)03d,%(levelname)-5s,%(name)s,Line %(lineno)d,%(message)s',
                                       datefmt='%Y-%m-%dT%H:%M:%S')
        logger = logging.getLogger(__name__)
        main(sys.argv[1],sys.argv[2])
    else:
        print("Running as import")
