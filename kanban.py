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
jSQLString = JiraJSONParser.formJQLQuery(
    projectId=config["default"]["issueKey"],
    filter=int(config["default"]["filterId"]),
    taskTypes=["Story"],
)
authToken = config["default"]["authentication-token"]
jiraBaseAPIURL = config["default"]["jiraURL"] + "/rest/api/2/issue/"
boardAPIURL = config["default"]["jiraURL"] + "/rest/api/2/search?jql=" + jSQLString

# fetch board issues
resp = requests.get(
    boardAPIURL, auth=TokenAuth(authToken), params={"Content-Type": "application/json"}
)

if resp.status_code != 200:
    raise Exception("Board information has not been fetched")

result = resp.json()

print("max {:d} out of {:d}".format(result["maxResults"], result["total"]))

# TODO: replace with full list when needed
narrowedList = result["issues"][:5]

for task in narrowedList:
    # fetch issue info
    issueParser = JiraJSONParser(authToken, jiraBaseAPIURL)
    issueParser.parseIssueJson(task)
    print(
        "Issue: "
        + task["key"]
        + ", type: "
        + issueParser.issueTypeName
        + ", status: "
        + issueParser.issueStatus
    )

    # if there are subtasks - fetch them one by one
    if issueParser.issueHasSubtasks:
        issueParser.getAndParseSubtasks(False)
        if len(issueParser.subtasksWOEstimation) > 0:
            print("Sub-tasks not estimated: " + ",".join(issueParser.subtasksWOEstimation))

    # print progress in 1 line
    progressInfoLine = issueParser.getCompactProgressInfo()
    if len(progressInfoLine) > 0:
        print(issueParser.getCompactProgressInfo())
    # warn if there is no estimation for task/bug
    elif issueParser.issueTypeName.lower() != "story":
        print("No estimation")

    print("")
