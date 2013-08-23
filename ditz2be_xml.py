#!/usr/bin/python2

import yaml
import glob
import os.path
import io

DITZ_DIR = ".ditz/"


class Issue(yaml.YAMLObject):
    yaml_tag = "!ditz.rubyforge.org,2008-03-06/issue"

    def __init__(self, title, desc, type_val, component, release, reporter,
                 status, disposition, creation_time, references, id,
                 log_events):
        self.title = title
        self.desc = desc
        self.type = type_val
        self.component = component
        self.release = release
        self.reporter = reporter
        self.status = status
        self.disposition = disposition
        self.creation_time = creation_time
        self.references = references
        self.id = id
        self.log_events = log_events

    def __str__(self):
        return "id = %s\ntitle: %s" % (self.id, self.title)


class Project(yaml.YAMLObject):
    yaml_tag = "!ditz.rubyforge.org,2008-03-06/project"

    def __init__(self, name, version, components, releases):
        self.name = name
        self.version = version
        self.components = []
        self.releases = releases

        for comp in components:
            self.components.append(yaml.load(comp))


class Component(yaml.YAMLObject):
    yaml_tag = "!ditz.rubyforge.org,2008-03-06/component"

    def __init__(self, name):
        self.name = name


issue_files = glob.glob(os.path.join(DITZ_DIR, "issue*.yaml"))
issues = []

for i_file in issue_files:
    issues.append(yaml.load(io.open(i_file)))

for iss in issues:
    print(iss)
