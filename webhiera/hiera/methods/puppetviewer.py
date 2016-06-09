#!/usr/bin/env python
"""
Requires: Python3

Application to parse and format hiera hierarchy in a readable fashion.

Currently supported formats: yaml
Supports groups and hiera merge with some configuration.
"""

import collections
import json
import os
import re
import sys

import requests
import yaml
from constance import config

from webhiera.hiera.models import HieraGroup, HieraMergeable
from webhiera.hiera.pdb.fetch import get_data


def get_hiera_data(node, show_modules=None, hide_modules=None, show_files=None, hide_files=None, debug=False):
    hiera_directory = config.HIERA_DATA_DIR

    # List of the groups used in your hiera hierarchy
    groups = list()
    for group in HieraGroup.objects.values('group_name'):
        groups.append(group['group_name'])

    # Dict of variables in your puppet modules and classes which have the
    # ability to enable hiera merge for certain parameters.
    # This is the way i had to do it because not all coders follow a certain
    # set of rules.. vas::users_allow_entries.. *cough*
    # Dict setup: name: default_value - This should be the default value set
    # in the module.
    for group in HieraGroup.objects.values('group_name'):
        groups.append(group['group_name'])

    hiera_mergeable = dict()
    for mergeable in HieraMergeable.objects.values('merge_parameter', 'default_value', 'merges_parameter'):
        hiera_mergeable[mergeable['merge_parameter']] = {
            'value': mergeable['default_value'],
            'parent': mergeable['merges_parameter']
        }

    # The class which we use to enables modules..
    param_con_class = config.PARAM_CON_CLASS

    # List of active classes which have been activated(This is populated and is
    # not something you should tamper with.
    pdb_query = {
        'query': '["and",["=","certname","%s"],["=","type","Class"]]' % node
    }
    resources = get_data('resources', query=pdb_query)

    act_class = ['classes']
    for resource in resources:
        act_class.append(resource['title'].lower())

    # Classes that can be activated through a module.. e.g (puppet-module-common)
    # Full name to parameter and class it activates
    # If you have more classes enabled via some puppet module in the same manner
    # as puppet-module-common (you are able to disable/enable) then you can add it
    # here.
    param_act_class = {}

    # URL to Puppet DB API Nodes - You should change this to your puppetdb server
    PDB_URL = ("%s/v3/nodes/%s/facts" % (config.PUPPETDB_HOST, node))

    ################
    #  End Config  #
    ################

    def check_config(path):
        """ Check path to the hiera data
            Check URL to Puppet DB API
        """
        # Fix path path if there is no trailing slash
        if not path.endswith('/'):
            path = path + '/'
        # Make sure path is a folder that exists
        if not os.path.isdir(path):
            print('Path set for Hiera_Directory does not exist!')
            sys.exit(1)
        # Attempt to contact the PuppetDB API and retrieve information
        r = requests.get(PDB_URL)
        if not r.status_code == 200:
            print('PuppetDB url is unreachable: %s' % PDB_URL)
            sys.exit(1)
        if not r.json():
            print("No fact results for node: %s" % node)
            sys.exit(1)
        else:
            return path, json.loads(r.text)

    def load_facts(json):
        """Load facts from json data
           Parses facts from the json data to a nice dictionary
        """
        # The json data comes in a list with each entry containing a dict.
        facter = {}
        facter_replace = {}
        for fact in json:
            if type(fact) == dict:
                facter[fact['name']] = fact['value']
        z = facter.copy()
        z.update(facter_replace)
        return z

    def parse_hiera_tree(path, facter):
        """Parses the hiera tree
           replaces the facts with values from facter
        """
        relevant_files = {}
        i = 1
        with open(path + 'hiera.yaml', 'r') as f:
            doc = yaml.load(f)
            for entry in doc[':hierarchy']:
                fact_match = re.findall(r'%{[:]*([aA-zZ]*)}', entry)
                buf = entry
                if fact_match:
                    for m in fact_match:
                        interpolation_method = re.findall(r'%{([:]*)' + m + '}', entry)
                        try:
                            buf = buf.replace("%{" + interpolation_method[0] + m + "}", facter[m])
                        except:
                            buf += '.yaml'
                    buf += '.yaml'
                elif not fact_match and entry not in groups:
                    buf += '.yaml'
                elif entry in groups and entry in facter:
                    list_of_groups = []
                    # Sort Groups alphabetically
                    for group in sorted(facter[entry].split(','), key=str.lower):
                        list_of_groups.append(entry + '/' + group + '.yaml')
                    buf = list_of_groups
                # Ignore entries that had missing facts because they are not
                # relevant
                if '%' not in buf:
                    relevant_files[i] = buf
                    i += 1
            return relevant_files

    def parse_hiera_files(path, hieratree):
        hiera_data = {}
        for k, v in hieratree.items():
            # Check to make sure that the file exists.
            # handle groups
            if type(v) is str:
                if os.path.isfile(path + v):
                    with open(path + v) as f:
                        hiera_data[k] = yaml.load(f)
            elif type(v) is list:
                group_data = {}
                for group in v:
                    if os.path.isfile(path + group):
                        with open(path + group) as f:
                            group_data[group] = yaml.load(f)
                hiera_data[k] = group_data
        return hiera_data

    def find_hiera_merge_values(hiera_data, hiera_merge):
        highest_key_val = 0
        for k in hiera_data:
            if k > highest_key_val:
                highest_key_val = k
        while highest_key_val > 0:
            try:
                for k, v in hiera_data[highest_key_val].items():
                    if k in hiera_merge:
                        if hiera_merge[k]['value'] != bool:
                            hiera_merge[k]['value'] = bool(v)
                        else:
                            hiera_merge[k]['value'] = v
            except:
                pass
            highest_key_val = highest_key_val - 1
        return hiera_merge

    def lookup_hiera_merged(parameter, merge_data):
        for k, v in merge_data.items():
            if v['parent'] == parameter:
                return v['value']
        return False

    def collect_data(hiera_data, hiera_mergeable, param_classes, list_of_classes):
        def check_if_collected(data, param):
            for k, v in data.items():
                for kk, vv in v.items():
                    if kk == param:
                        return True
            return False

        # Check if class already exists in list or if it should be added.

        def check_act_class(class_name, class_list):
            if class_name not in class_list:
                class_list.append(class_name)
            return class_list

        # Check if the class name exists in the paramater dictionary

        def class_in_param(key_name, param_list):
            return key_name in param_list

        collected_data = {}
        for k, v in hiera_data.items():
            if type(v) is dict:
                collected_data[k] = {}
                for kk, vv in v.items():
                    if kk.endswith('.yaml'):
                        for kkk, vvv in vv.items():
                            mergable = lookup_hiera_merged(kkk, hiera_mergeable)
                            collected = check_if_collected(collected_data, kkk)
                            if not mergable and collected:
                                continue
                            if class_in_param(kkk, param_classes):
                                if vvv == "true":
                                    list_of_classes = check_act_class(
                                        param_classes[kkk], list_of_classes)
                            elif kkk == param_con_class:
                                for item in vvv:
                                    list_of_classes = check_act_class(
                                        item, list_of_classes)
                            if mergable and not collected:
                                collected_data[k][kkk] = vvv
                            elif mergable and collected:
                                if kkk in collected_data[k]:
                                    if isinstance(vvv, dict) and isinstance(collected_data[k][kkk], dict):
                                        collected_data[k][kkk].update(vvv)
                                    else:
                                        collected_data[k][kkk] += vvv
                                else:
                                    collected_data[k][kkk] = vvv
                            elif not mergable and not collected:
                                collected_data[k][kkk] = vvv
                    else:
                        mergable = lookup_hiera_merged(kk, hiera_mergeable)
                        collected = check_if_collected(collected_data, kk)
                        if not mergable and collected:
                            continue
                        if class_in_param(kk, param_classes):
                            if vv == "true":
                                list_of_classes = check_act_class(
                                    param_classes[kk], list_of_classes)

                        elif kk == param_con_class:
                            for item in vv:
                                list_of_classes = check_act_class(
                                    item, list_of_classes)
                        if mergable:
                            collected_data[k][kk] = vv
                        elif not mergable and not collected:
                            collected_data[k][kk] = vv
        return collected_data, list_of_classes

    def print_data(data, classes):
        indent_key = '&nbsp;&nbsp;&nbsp;&nbsp;'

        class c:
            BOLD = ''
            H = ''
            B = ''
            G = ''
            Y = ''
            V = ''
            C = ''
            P = ''
            W = ''
            F = ''
            E = ''

        def module_name(param):
            return param.split(':')[0]

        def print_stuff(data_dict, level, classes):
            output = []
            if type(data_dict) is dict:
                for k, v in sorted(data_dict.items()):
                    if not module_name(k) in classes and level is 0:
                        if not debug:
                            continue
                    if level == 0 and show_modules:
                        if module_name(k) not in show_modules:
                            continue
                    if level == 0 and hide_modules:
                        if module_name(k) in hide_modules:
                            continue

                    if type(v) is dict:
                        output.append(indent_key * level + "<strong>%s</strong>" % k)
                        output += print_stuff(v, level + 1, classes)
                    elif type(v) is list:
                        output.append(indent_key * level + "<strong>%s</strong>" % k)
                        output += print_stuff(v, level + 1, classes)
                    elif type(v) is bool:
                        output.append(indent_key * level + "<strong>%s</strong>: <code>%s</code>" % (k, v))
                    elif type(v) is int:
                        output.append(indent_key * level + "<strong>%s</strong>: <code>%s</code>" % (k, v))
                    else:
                        output.append(
                            indent_key * level + "<strong>%s</strong>: <code>%s</code>" % (k, v.replace('\n', '<br>')))
            elif type(data_dict) is list:
                for item in sorted(data_dict):
                    output.append(indent_key * level + "<code>%s</code>" % item.replace('\n', '<br>'))
            elif type(data_dict) is str:
                output.append(indent_key * level + "<code>%s</code>" % data_dict.replace('\n', '<br>'))
            elif type(data_dict) is bool:
                if data_dict:
                    tmp_data_dict = 'true'
                else:
                    tmp_data_dict = 'false'
                output.append(indent_key * level + "<code>%s</code>" % tmp_data_dict)
            return output

        data_result = []

        for k, v in data.items():
            if type(hieratree[k]) != list:
                # Print filename
                if show_files:
                    if hieratree[k] not in show_files:
                        continue
                if hide_files:
                    if hieratree[k] in hide_files:
                        continue

                recurse_result = []
                for kk, vv in sorted(v.items()):
                    if not module_name(kk) in classes:
                        if not debug:
                            continue
                    if show_modules:
                        if module_name(kk) not in show_modules:
                            continue
                    if hide_modules:
                        if module_name(kk) in hide_modules:
                            continue
                    # Print parameter name
                    recurse_result.append("<strong>%s</strong>" % kk)
                    recurse_result += print_stuff(vv, 1, classes)

                if recurse_result:
                    data_result.append(
                        '<div class="panel panel-default"><div class="panel-heading">'
                        '<h3 class="panel-title">' + hieratree[k] + '</h3>'
                                                                    '</div><div class="panel-body">'
                    )
                    data_result += recurse_result
                    data_result.append('</div></div>')

            # THIS IS FOR GROUPS
            elif type(hieratree[k]) is list:
                recurse_result = []
                groups = ','.join(hieratree[k])
                if show_files:
                    if groups not in show_files:
                        continue
                if hide_files:
                    if groups in hide_files:
                        continue
                # Print filename

                recurse_result = print_stuff(v, 0, classes)
                if recurse_result:
                    data_result.append(
                        '<div class="panel panel-default"><div class="panel-heading">'
                        '<h3 class="panel-title">' + groups + '</h3>'
                                                              '</div><div class="panel-body">'
                    )
                    data_result += recurse_result
                    data_result.append('</div></div>')

        data_result = '\n<br>\n'.join(data_result)
        return data_result

    hiera_directory, jdata = check_config(hiera_directory)
    facts = load_facts(jdata)

    hieratree = parse_hiera_tree(hiera_directory, facts)
    hieratree = collections.OrderedDict(sorted(hieratree.items()))

    hiera_data = parse_hiera_files(hiera_directory, hieratree)
    hiera_data = collections.OrderedDict(sorted(hiera_data.items()))

    hiera_mergeable = find_hiera_merge_values(hiera_data, hiera_mergeable)

    sorted_data, act_class = collect_data(
        hiera_data, hiera_mergeable, param_act_class, act_class)
    sorted_data = collections.OrderedDict(sorted(sorted_data.items()))

    return print_data(sorted_data, act_class)
