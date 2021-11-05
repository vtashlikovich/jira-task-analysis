import requests
from requests.auth import AuthBase

RED_COLOR = "\033[91m"
GREEN_COLOR = "\033[92m"
WARN_BG_COLOR = "\033[43m"
WARN_COLOR = "\033[93m"
BLUE_COLOR = "\033[94m"
ENDTERM = "\033[0m"


class TokenAuth(AuthBase):
    """Implements a custom authentication scheme."""

    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers["Authorization"] = "Basic " + self.token
        return r


# ==============================================================================
class JiraJSONParser:
    """Collecting & parsing Jira tasks via REST API"""

    issueHasSubtasks = False
    issueJson = {}
    subtasksCount = 0
    subtasksWOEstimationCount = 0
    subtasksWOEstimation = []
    subtasksOriginalEstimation = 0
    issueTypeName = "Issue"
    issueProgress = {}
    issueAggregateProgress = {}
    issueOriginalTypeName = ""
    issueStatus = ""
    requestParameters = {"Content-Type": "application/json"}
    authToken = ""
    jiraBaseAPIURL = ""

    def __init__(self, authToken: str = "", jiraBaseAPIURL: str = ""):
        self.authToken = authToken
        self.jiraBaseAPIURL = jiraBaseAPIURL

    def getAndParse(self, issueKey: str):
        self.issueHasSubtasks = False
        self.issueJson = {}
        self.subtasksCount = 0
        self.subtasksWOEstimationCount = 0
        self.subtasksWOEstimation = []
        self.subtasksOriginalEstimation = 0
        self.issueTypeName = "Issue"
        self.issueProgress = {}
        self.issueAggregateProgress = {}
        self.issueOriginalTypeName = ""
        self.issueStatus = ""

        resp = requests.get(
            self.jiraBaseAPIURL + issueKey,
            auth=TokenAuth(self.authToken),
            params=self.requestParameters,
        )

        if resp.status_code != 200:
            raise Exception(
                "Issue {} details response code: {}".format(issueKey, resp.status_code)
            )

        self.parseIssueJson(resp.json())

    def parseIssueJson(self, issueExternalJson: str):
        self.issueJson = issueExternalJson
        self.subtasksCount = len(self.issueJson["fields"]["subtasks"])
        self.issueHasSubtasks = (
            not bool(self.issueJson["fields"]["issuetype"]["subtask"])
            and self.subtasksCount > 0
        )
        if self.subtasksCount > 0:
            self.issueTypeName = "Story"

        self.issueOriginalTypeName = self.issueJson["fields"]["issuetype"]["name"]
        self.issueStatus = self.issueJson["fields"]["status"]["name"]

        self.issueProgress["originalEstimate"] = 0
        if (
            "timetracking" in self.issueJson["fields"]
            and "originalEstimateSeconds" in self.issueJson["fields"]["timetracking"]
        ):
            self.issueProgress["originalEstimate"] = self.issueJson["fields"][
                "timetracking"
            ]["originalEstimateSeconds"]
        self.issueProgress["total"] = self.issueJson["fields"]["progress"]["total"]
        self.issueProgress["progress"] = self.issueJson["fields"]["progress"][
            "progress"
        ]
        self.issueProgress["progressPercent"] = 0
        if "percent" in self.issueJson["fields"]["progress"]:
            self.issueProgress["progressPercent"] = self.issueJson["fields"][
                "progress"
            ]["percent"]
        self.issueProgress["timeLeft"] = 0
        if self.issueJson["fields"]["timeestimate"] != None:
            self.issueProgress["timeLeft"] = self.issueJson["fields"]["timeestimate"]
        self.issueProgress["timeLeftOriginal"] = 0
        if self.issueProgress["originalEstimate"] > 0:
            self.issueProgress["timeLeftOriginal"] = (
                self.issueProgress["originalEstimate"] - self.issueProgress["progress"]
            )

        self.issueAggregateProgress["originalEstimate"] = 0
        self.issueAggregateProgress["total"] = 0
        self.issueAggregateProgress["progress"] = 0
        self.issueAggregateProgress["progressPercent"] = 0
        self.issueAggregateProgress["timeLeft"] = 0
        if (
            self.issueHasSubtasks
            and self.issueJson["fields"]
            and self.issueJson["fields"]["aggregateprogress"]
        ):
            if (
                self.issueJson["fields"]
                and self.issueJson["fields"]["aggregatetimeoriginalestimate"]
            ):
                self.issueAggregateProgress["originalEstimate"] = self.issueJson[
                    "fields"
                ]["aggregatetimeoriginalestimate"]
            self.issueAggregateProgress["total"] = self.issueJson["fields"][
                "aggregateprogress"
            ]["total"]
            self.issueAggregateProgress["progress"] = self.issueJson["fields"][
                "aggregateprogress"
            ]["progress"]
            if "percent" in self.issueJson["fields"]["aggregateprogress"]:
                self.issueAggregateProgress["progressPercent"] = self.issueJson[
                    "fields"
                ]["aggregateprogress"]["percent"]
        if self.issueJson["fields"]["aggregatetimeestimate"] != None:
            self.issueAggregateProgress["timeLeft"] = self.issueJson["fields"][
                "aggregatetimeestimate"
            ]
        self.issueAggregateProgress["timeLeftOriginal"] = 0
        if self.issueAggregateProgress["originalEstimate"] > 0:
            self.issueAggregateProgress["timeLeftOriginal"] = (
                self.issueAggregateProgress["originalEstimate"]
                - self.issueAggregateProgress["progress"]
            )

    def getAndParseSubtasks(self, logProgress: bool = True):
        self.subtasksWOEstimationCount = 0
        self.subtasksOriginalEstimation = 0
        self.subtasksWOEstimation = []

        i = 0
        if self.issueHasSubtasks:
            printLine = "Subtasks count: " + str(self.subtasksCount) + " "

            if logProgress:
                print("")
                print(printLine)

            for subtask in self.issueJson["fields"]["subtasks"]:

                if logProgress:
                    # sys.stdout.write('\\')
                    loader = "/"
                    if i == 1:
                        loader = "\\"
                        i = 0
                    else:
                        i = 1
                    print("\033[F" + printLine + loader)

                subtaskURL = self.jiraBaseAPIURL + subtask["key"]
                resp = requests.get(
                    subtaskURL,
                    auth=TokenAuth(self.authToken),
                    params=self.requestParameters,
                )

                if resp.status_code != 200:
                    raise Exception(
                        "Issue {} details response code: {}".format(
                            subtask["key"], resp.status_code
                        )
                    )

                subtaskJson = resp.json()
                if "originalEstimate" not in subtaskJson["fields"]["timetracking"]:
                    self.subtasksWOEstimation.append(subtask["key"])
                    if subtask["fields"]["status"]["name"] != "Done":
                        self.subtasksWOEstimationCount += 1
                        # print(', ESTIMATION needed!')
                else:
                    if (
                        "originalEstimateSeconds"
                        in subtaskJson["fields"]["timetracking"]
                    ):
                        self.subtasksOriginalEstimation += subtaskJson["fields"][
                            "timetracking"
                        ]["originalEstimateSeconds"]
                        # print(', originalEstimate = ', self.convertMsToHours(subtaskJson['fields']['timetracking']['originalEstimateSeconds']))

        self.subtasksOriginalEstimation = self.convertMsToHours(
            self.subtasksOriginalEstimation
        )

    def convertMsToHours(self, valueMs: int, showUnit: bool = True) -> str:
        result = str(valueMs / 3600)
        if showUnit:
            result += "h"
        return result

    @staticmethod
    def formJQLQuery(
        projectId: str,
        excludeDone: bool = True,
        excludeOpen: bool = True,
        filter: int = 0,
        taskTypes=["Task", "Story", "Bug"],
    ) -> str:
        jSQLString = (
            'project = "' + projectId + '" and type in (' + ",".join(taskTypes) + ")"
        )
        if filter > 0:
            jSQLString += " AND filter = " + str(filter)
        if excludeDone:
            jSQLString += " AND status != Done"
        if excludeOpen:
            jSQLString += " AND status != Open"
        jSQLString += " ORDER BY created DESC"
        return jSQLString

    # --- output related ------------------------------------------------

    def printGeneralInfo(self):
        print("Issue type:", self.issueOriginalTypeName)
        print("Are there subtasks?:", self.issueHasSubtasks)

        termColor = WARN_BG_COLOR
        if self.issueStatus == "Done":
            termColor = GREEN_COLOR
        if self.issueStatus == "To Do" or self.issueStatus == "Open":
            termColor = BLUE_COLOR
        print(self.issueTypeName + " status:", termColor + self.issueStatus + ENDTERM)

    def printProgressInfo(self):
        if (
            self.issueProgress["total"] > 0
            or self.issueProgress["originalEstimate"] > 0
        ):
            print("")
            print("Exact " + self.issueTypeName.lower() + " progress:")
            print(
                " Original estimation = ",
                self.convertMsToHours(self.issueProgress["originalEstimate"]),
            )
            print(" Total:", self.convertMsToHours(self.issueProgress["total"]))
            print(" Progress:", self.convertMsToHours(self.issueProgress["progress"]))
            print(" ", str(self.issueProgress["progressPercent"]) + "%")
            timeLeftColor = GREEN_COLOR
            if self.issueProgress["timeLeft"] <= 0:
                timeLeftColor = RED_COLOR
            print(
                " Time left: ",
                timeLeftColor
                + self.convertMsToHours(self.issueProgress["timeLeft"])
                + ENDTERM,
            )
            timeLeftColor = GREEN_COLOR
            if self.issueProgress["timeLeftOriginal"] <= 0:
                timeLeftColor = RED_COLOR
            print(
                " Time left (original): ",
                timeLeftColor
                + self.convertMsToHours(self.issueProgress["timeLeftOriginal"])
                + ENDTERM,
            )

        if self.issueAggregateProgress["total"] > 0 and self.issueHasSubtasks:
            print("")
            print("Aggregated progress:")
            print(
                " Original estimation = ",
                self.convertMsToHours(self.issueAggregateProgress["originalEstimate"]),
            )
            print(
                " Total:", self.convertMsToHours(self.issueAggregateProgress["total"])
            )
            print(
                " Progress:",
                self.convertMsToHours(self.issueAggregateProgress["progress"]),
            )
            print(" ", str(self.issueAggregateProgress["progressPercent"]) + "%")
            timeLeftColor = GREEN_COLOR
            if self.issueAggregateProgress["timeLeft"] <= 0:
                timeLeftColor = RED_COLOR
            print(
                " Time left: ",
                timeLeftColor
                + self.convertMsToHours(self.issueAggregateProgress["timeLeft"])
                + ENDTERM,
            )
            timeLeftColor = GREEN_COLOR
            if self.issueAggregateProgress["timeLeftOriginal"] <= 0:
                timeLeftColor = RED_COLOR
            print(
                " Time left (original): ",
                timeLeftColor
                + self.convertMsToHours(self.issueAggregateProgress["timeLeftOriginal"])
                + ENDTERM,
            )

    def getCompactProgressInfo(self) -> str:
        originalInfoLine = ""
        if (
            self.issueProgress["total"] > 0
            or self.issueProgress["originalEstimate"] > 0
        ):
            originalInfoLine += (
                "Original: e"
                + self.convertMsToHours(self.issueProgress["originalEstimate"])
                + ", p"
            )
            totalColor = ""
            totalEndColor = ""
            if self.issueProgress["total"] > self.issueProgress["originalEstimate"]:
                totalColor = WARN_COLOR
                totalEndColor = ENDTERM
            originalInfoLine += (
                self.convertMsToHours(self.issueProgress["progress"], False)
                + "/"
                + totalColor
                + self.convertMsToHours(self.issueProgress["total"])
                + totalEndColor
            )
            originalInfoLine += ", " + str(self.issueProgress["progressPercent"]) + "%"
            timeLeftColor = GREEN_COLOR
            if self.issueProgress["timeLeft"] <= 0:
                timeLeftColor = RED_COLOR
            originalInfoLine += (
                ", l"
                + timeLeftColor
                + self.convertMsToHours(self.issueProgress["timeLeft"], False)
                + ENDTERM
            )
            timeLeftColor = GREEN_COLOR
            if self.issueProgress["timeLeftOriginal"] <= 0:
                timeLeftColor = RED_COLOR
            originalInfoLine += (
                ", lo"
                + timeLeftColor
                + self.convertMsToHours(self.issueProgress["timeLeftOriginal"])
                + ENDTERM
            )

        if self.issueAggregateProgress["total"] > 0 and self.issueHasSubtasks:
            if len(originalInfoLine) > 0:
                originalInfoLine += "\r\n"
            originalInfoLine += (
                "Aggregated: e"
                + self.convertMsToHours(self.issueAggregateProgress["originalEstimate"])
                + ", p"
            )
            totalColor = ""
            totalEndColor = ""
            if (
                self.issueAggregateProgress["total"]
                > self.issueAggregateProgress["originalEstimate"]
            ):
                totalColor = WARN_COLOR
                totalEndColor = ENDTERM
            originalInfoLine += (
                self.convertMsToHours(self.issueAggregateProgress["progress"], False)
                + "/"
                + totalColor
                + self.convertMsToHours(self.issueAggregateProgress["total"])
                + totalEndColor
            )
            originalInfoLine += (
                ", " + str(self.issueAggregateProgress["progressPercent"]) + "%"
            )

            timeLeftColor = GREEN_COLOR
            if self.issueAggregateProgress["timeLeft"] <= 0:
                timeLeftColor = RED_COLOR
            originalInfoLine += (
                ", l"
                + timeLeftColor
                + self.convertMsToHours(self.issueAggregateProgress["timeLeft"], False)
                + ENDTERM
            )
            timeLeftColor = GREEN_COLOR
            if self.issueAggregateProgress["timeLeftOriginal"] <= 0:
                timeLeftColor = RED_COLOR
            originalInfoLine += (
                ", lo"
                + timeLeftColor
                + self.convertMsToHours(self.issueAggregateProgress["timeLeftOriginal"])
                + ENDTERM
            )

        return originalInfoLine

    def printSubtasksStats(self):
        if self.issueHasSubtasks:
            print("")
            print("Sub-tasks initial estimation: ", self.subtasksOriginalEstimation)
            print("Sub-tasks with NO estimation: ", self.subtasksWOEstimationCount)
