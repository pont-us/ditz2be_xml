#!/usr/bin/python
# -*- coding: utf-8 -*-
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the original
# work is properly attributed to Matěj Cepl.
# The name of Matěj Cepl may not be used to endorse or promote
# products derived from this software without specific prior
# written permission.
# This software is provided by Matěj Cepl "AS IS" and without any
# express or implied warranties.

import yaml
from xml.etree import ElementTree as et
import logging
import glob
import os.path
import io
import re

logging.basicConfig(format='%(levelname)s:%(funcName)s:%(message)s',
                    level=logging.DEBUG)

DITZ_DIR = ".ditz/"

# A mapping from Ditz status strings to Bugs Everywhere status strings.
STATUS_MAP = \
{":unstarted"   : "open",
 ":paused"      : "open",
 ":in_progress" : "open",
 ":closed"      : "fixed"
}

def _xml_indent(elem, level=0):
    """Indent an XML element and its children.

    The element is modified in-place.

    Args:
        elem: the element to indent
        level: the current level of indentation

    """
    i = "\n" + level * "  "
    if len(elem) != 0:
        if not (elem.text and elem.text.strip()):
            elem.text = i + "  "
        for e in elem:
            _xml_indent(e, level + 1)
        if not (e.tail and e.tail.strip()):
            e.tail = i
    else:
        if level and not(elem.tail and elem.tail.strip()):
            elem.tail = i


def make_comment(body, who, when):
    """Construct a BE XML element representing a comment.

    Args:
        body: body text of the comment
        who: name of the author of the comment
        when: date of comment, in format
              "Wed, 01 Jan 2014 12:00:00 +0000"

    Returns:
        an xml.etree.ElementTree.Element object representing
        the supplied data
    """
    out = et.Element("comment")
    et.SubElement(out, "author").text = who
    et.SubElement(out, "date").text = when
    et.SubElement(out, "content-type").text = "text/plain"
    # BE import doesn't like empty comment bodies
    if body=="": body = "(no content)"
    et.SubElement(out, "body").text = body
    return out


class Issue(yaml.YAMLObject):
    """A YAML object representing a Ditz issue.

    The object can be created and the fields populated automatically using
    yaml.load.
    """

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

    @staticmethod
    def __format_time(in_time):
        """Convert a Ditz timestamp to a BE timestamp.
        
        Args:
            in_time: timestamp string with format "2012-02-23T22:09:58Z"

        Return:
            timestamp string with format "Thu, 23 Feb 2012 22:09:58 +0000"
        """
        logging.debug("in_time = %s", in_time)
        out = in_time.strftime("%a, %d %b %Y %H:%M:%S %z+0000")
        logging.debug("out = %s, out")
        return out

    @staticmethod
    def __convert_status(ditz_status):
        return STATUS_MAP[ditz_status]

    def __add_subelement(self, iss_attr, trg_elem, convert=None):
        if getattr(self, iss_attr) is not None:
            if convert:
                value = convert(getattr(self, iss_attr))
            else:
                value = getattr(self, iss_attr)
            logging.debug("iss_attr = %s, value = %s", iss_attr, value)
            et.SubElement(self.bug, trg_elem).text = value

    def to_XML(self):
        """Return a BE XML representation of this Issue.
        """
        self.bug = et.Element("bug")

        self.__add_subelement("creation_time", "created",
                              self.__format_time)
        self.__add_subelement("title", "summary")
        self.__add_subelement("status", "status",
                              self.__convert_status)
        self.__add_subelement("reporter", "reporter")
        self.__add_subelement("reporter", "creator")
        # FIXME
        #self.__add_subelement("assignee", "assigned")

        if self.desc is not None:
            self.bug.append(make_comment(self.desc,
                                         self.reporter,
                                         self.__format_time(
                                             self.creation_time)))

        for date, reporter, action, comment in self.log_events:
            if comment is not None and comment != "":
                self.bug.append(make_comment(comment,
                                             reporter,
                                             self.__format_time(
                                                 date)))


        #for comment in get_comments(cnf['git_user'], cnf['git_password'],
        #                            cnf['repo'], iss[u"number"]):
        #    self.bug.append(make_comment(comment[u"body"],
        #               comment[u"user"][u"login"],
        #               format_time(comment[u"updated_at"])))

        return self.bug

    def __str__(self):
        return "id = %s\ntitle: %s\ncreated: %s" % (self.id, self.title,
                                                    self.creation_time)


class Project(yaml.YAMLObject):
    """A YAML object representing a Ditz Project.

    The object can be created and the fields populated automatically using
    yaml.load.
    """
    yaml_tag = "!ditz.rubyforge.org,2008-03-06/project"

    def __init__(self, name, version, components, releases):
        self.name = name
        self.version = version
        self.components = []
        self.releases = releases

        for comp in components:
            self.components.append(yaml.load(comp))


class Component(yaml.YAMLObject):
    """A YAML object representing a Ditz Component.

    The object can be created and the fields populated automatically using
    yaml.load.
    """
    yaml_tag = "!ditz.rubyforge.org,2008-03-06/component"

    def __init__(self, name):
        self.name = name

def fix_ditz_yaml(ditz_string):
    """Correct problems with Ditz YAML.

    Ditz doesn't put double quotes around titles starting with the
    "`" character, and encodes non-ASCII characters in a non-standard
    way. This function rewrites a Ditz quasi-YAML into a well-formed
    YAML string which can be read by yaml.load without problems.

    Args:
        ditz_string: an issue record in "ditz-flavoured" YAML

    Return:
        the equivalent record in specification-compliant YAML 1.1
    """

    # Put " characters around titles beginning with `
    result = re.sub("title: (`.*)\n", r'title: "\1"\n', ditz_string)

    # Ditz represents 16-bit Unicode characters as three consecutive
    # \x.. escapes representing the bytes of a UTF-8 encoding,
    # rather than (as YAML specifies) a \u.... escape or the encoded
    # UTF-8 character itself (UTF-8 is YAML's default encoding anyway
    # so escapes are unnecessary). However, we can't just do a blanket
    # decode on the whole string since it would also replace \n escapes
    # required for multiple paragraphs in text block (and possibly other
    # things I haven't thought of). So we selectively decode the \x
    # escapes only.
    matches = re.findall(r"((\\x..)+)", result)
    for escape, _ in matches:
        utf8 = escape.decode("string_escape").decode("utf-8")
        result = result.replace(escape, utf8)

    return result

def main():
    out_xml = et.fromstring("""<be-xml>
        <version>
        </version>
    </be-xml>""")

    issue_files = glob.glob(os.path.join(DITZ_DIR, "issue*.yaml"))
    logging.debug("issue_files = %s", issue_files)

    for i_file in issue_files:
        with io.FileIO(i_file) as issue_io:
            issue_io = io.FileIO(i_file)
            issue_str = issue_io.readall()
        issue = yaml.load(fix_ditz_yaml(issue_str))
        out_xml.append(issue.to_XML())

    _xml_indent(out_xml)
    print et.tostring(out_xml, "utf-8")


if __name__ == '__main__':
    main()
