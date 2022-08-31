#!/usr/bin/env python

import configparser
import sys
from jiraparser import JiraJSONParser, TokenAuth
import requests
from requests.auth import AuthBase

""" Getting a list of issues connected to a board id (defined by configuration) and printing analysis information """

# read config
config = configparser.ConfigParser()
config.read("config.ini")

# prepare parameters
# if there is a Board in config (filterId) ->
if "filterId" in config["default"]:
    jsql_query = JiraJSONParser.form_jql_query(
        projectId=config["default"]["issueKey"],
        filter=int(config["default"]["filterId"]),
        taskTypes=["Story", "Task"],
    )
# if Board is not pointed ->
else:
    jsql_query = JiraJSONParser.form_jql_query(
        projectId=config["default"]["issueKey"],
        taskTypes=["Story", "Task"],
    )

auth_token = config["default"]["authentication-token"]
jira_base_api_url = config["default"]["jiraURL"] + "/rest/api/2/issue/"
board_api_url = config["default"]["jiraURL"] + "/rest/api/2/search?jql=" + jsql_query

# fetch board issues
resp = requests.get(
    board_api_url, auth=TokenAuth(auth_token), params={"Content-Type": "application/json"}
)

if resp.status_code != 200:
    raise Exception("Board information has not been fetched")

result = resp.json()

print("max {:d} out of {:d}".format(result["maxResults"], result["total"]))

narrowed_list = result["issues"]
# narrowed_list = result["issues"][:3]

for task in narrowed_list:
    # fetch issue info
    issue_parser = JiraJSONParser(auth_token, jira_base_api_url)
    issue_parser.parse_issue_json(task)
    print(
        "Issue: "
        + task["key"]
        + ", type: "
        + issue_parser.issue_type_name
        + ", status: "
        + issue_parser.issue_status
    )

    # if there are subtasks - fetch them one by one
    if issue_parser.issue_has_subtasks:
        issue_parser.get_parse_subtasks(False)
        if len(issue_parser.subtasks_wo_estimation) > 0:
            print("Sub-tasks not estimated: " + ",".join(issue_parser.subtasks_wo_estimation))

    # print progress in 1 line
    progress_info_line = issue_parser.get_compact_progress_info()
    if len(progress_info_line) > 0:
        print(issue_parser.get_compact_progress_info())
    # warn if there is no estimation for task/bug
    elif issue_parser.issue_type_name.lower() != "story":
        print("No estimation")

    print("")
