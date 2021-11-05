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

issueKey = sys.argv[1]
authToken = config["default"]["authentication-token"]
jiraBaseAPIURL = config["default"]["jiraURL"] + "/rest/api/2/issue/"

# action: get a single issue
issueParser = JiraJSONParser(authToken, jiraBaseAPIURL)
issueParser.getAndParse(issueKey)

# general information
issueParser.printGeneralInfo()

# story progress info
issueParser.printProgressInfo()

# subtasks info
issueParser.getAndParseSubtasks()
issueParser.printSubtasksStats()

# TODO: print tasks WO estimation and their status
