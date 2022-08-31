#!/usr/bin/env python

import configparser
import sys
from jiraparser import JiraJSONParser

""" Getting a single issue defined by income argument and print analysis information """

# read config
# TODO: make config file customized via arguments
config = configparser.ConfigParser()
config.read("config.ini")

# getting issue key out of argument
if len(sys.argv) < 2:
    print("\033[91mWarning\033[0m: missing issue key")
    print(
        "Please use issue key for examination as incoming command line parameter. Example:"
    )
    print("> python index.py JIRA-15")
    exit(1)

issue_key = sys.argv[1]
auth_token = config["default"]["authentication-token"]
jira_base_api_url = config["default"]["jiraURL"] + "/rest/api/2/issue/"

# action: get a single issue
issue_parser = JiraJSONParser(auth_token, jira_base_api_url)
issue_parser.get_and_parse(issue_key)

# general information
issue_parser.print_general_info()

# story progress info
issue_parser.print_progress_info()

# subtasks info
issue_parser.get_parse_subtasks()
issue_parser.print_subtasks_stats()

# TODO: print tasks WO estimation and their status
