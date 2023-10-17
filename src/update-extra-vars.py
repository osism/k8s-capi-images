#!/usr/bin/python3
#
# Script to fetch the latest version of kubernetes by the given file.
#
###############################################################################

import json
import sys
import urllib.parse
import urllib.request


###############################################################################
# Variables
###############################################################################

github_api = "https://api.github.com/repos/kubernetes/kubernetes/tags"
file = sys.argv[1]


###############################################################################
# Functions
###############################################################################


def load_file(file):
    with open(file) as json_load_file:
        data = json.load(json_load_file)
    return data


def traverse_pagination():
    # check, how many pages can be traversed by using the mozilla header
    # more information:
    # https://docs.github.com/en/rest/guides/traversing-with-pagination
    query_url = github_api + "?q=addClass+user:mozilla&per_page=100"
    with urllib.request.urlopen(query_url) as url:
        result = url.getheader("link")

    # turn this answer
    # <https://api.github.com/repositories/20580498/tags?q=addClass+user%3Amo\
    # zilla&per_page=100&page=2>; rel="next", <https://api.github.com/reposit\
    # ories/20580498/tags?q=addClass+user%3Amozilla&per_page=100&page=8>; rel\
    # ="last"
    # into a list
    # [
    #  '<https://api.github.com/repositories/20580498/tags?q',
    #  'addClass+user%3Amozilla&per_page',
    #  '100&page',
    #  '2>; rel',
    #  '"next" <https://api.github.com/repositories/20580498/tags?q',
    #  'addClass+user%3Amozilla&per_page',
    #  '100&page',
    #  '8>; rel',
    #  '"last"'
    # ]
    result = result.split("=")
    # get only the 8th entry: '8>; rel'
    result = result[7]
    # strip away the html stuff to get only the number of pages
    result = result.split(">")[0]

    return int(result)


def update_version(data):
    new_version = "v0.0.0"
    versions_list = []
    number_of_pages = traverse_pagination()

    # loop number of pages and query 100 tags each time
    # and break, if we found a matching tag to avoid too much api queries
    for page in range(number_of_pages):
        query_url = github_api + "?per_page=100&page=" + str(page)
        with urllib.request.urlopen(query_url) as url:
            # check the 100 tags if they are valid and append
            # them to the list "versions"
            for entry in json.loads(url.read().decode()):
                if (
                    "rc" not in entry["name"]
                    and "alpha" not in entry["name"]
                    and "beta" not in entry["name"]
                ):
                    versions_list.append(entry["name"])

            # find the first entry in version_list that matches
            # the series (v1.28 matches v1.28.3)
            for entry in versions_list:
                if data["kubernetes_series"] in entry:
                    new_version = entry
                    break

            # if new_version is set, a match was found. The page loop can be
            # exited by a break.
            # otherwise the loop will continue and search for a match.
            if not new_version == "v0.0.0":
                break

    # check if we really found a match
    if not new_version == "v0.0.0":
        # e.g. 1.28.2-1.1
        data["kubernetes_deb_version"] = new_version[1:] + "-1.1"
        # e.g. v1.28.2
        data["kubernetes_semver"] = new_version
        # e.g. v1.28
        data["kubernetes_series"] = (
            new_version.split(".")[0] + "." + new_version.split(".")[1]
        )

    return data


def dump_file(file, data):
    with open(file, "w") as fp:
        json.dump(data, fp, indent=4, sort_keys=True)
        fp.write("\n")


###############################################################################
# Main
###############################################################################

original_data = load_file(file)
updated_data = update_version(original_data)
dump_file(file, updated_data)
