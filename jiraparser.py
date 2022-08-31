import requests
from requests.auth import AuthBase

RED_COLOR = "\033[91m"
GREEN_COLOR = "\033[92m"
WARN_BG_COLOR = "\033[43m"
WARN_COLOR = "\033[95m"
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

    issue_has_subtasks = False
    issue_json = {}
    subtasks_count = 0
    subtasks_wo_estimation_count = 0
    subtasks_wo_estimation = []
    subtasks_original_estimation = 0
    issue_type_name = "Issue"
    issue_progress = {}
    issue_aggregate_progress = {}
    issue_original_type_name = ""
    issue_status = ""
    request_params = {"Content-Type": "application/json"}
    auth_token = ""
    jira_base_api_url = ""

    def __init__(self, authToken: str = "", jiraBaseAPIURL: str = ""):
        self.auth_token = authToken
        self.jira_base_api_utl = jiraBaseAPIURL

    def get_and_parse(self, issueKey: str):
        self.issue_has_subtasks = False
        self.issue_json = {}
        self.subtasks_count = 0
        self.subtasks_wo_estimation_count = 0
        self.subtasks_wo_estimation = []
        self.subtasks_original_estimation = 0
        self.issue_type_name = "Issue"
        self.issue_progress = {}
        self.issue_aggregate_progress = {}
        self.issue_original_type_name = ""
        self.issue_status = ""

        resp = requests.get(
            self.jira_base_api_utl + issueKey,
            auth=TokenAuth(self.auth_token),
            params=self.request_params,
        )

        if resp.status_code != 200:
            raise Exception(
                "Issue {} details response code: {}".format(issueKey, resp.status_code)
            )

        self.parse_issue_json(resp.json())

    def parse_issue_json(self, issueExternalJson: str):
        self.issue_json = issueExternalJson
        self.subtasks_count = len(self.issue_json["fields"]["subtasks"])
        self.issue_has_subtasks = (
            not bool(self.issue_json["fields"]["issuetype"]["subtask"])
            and self.subtasks_count > 0
        )
        if self.subtasks_count > 0:
            self.issue_type_name = "Story"

        self.issue_original_type_name = self.issue_json["fields"]["issuetype"]["name"]
        self.issue_status = self.issue_json["fields"]["status"]["name"]

        self.issue_progress["originalEstimate"] = 0
        if (
            "timetracking" in self.issue_json["fields"]
            and "originalEstimateSeconds" in self.issue_json["fields"]["timetracking"]
        ):
            self.issue_progress["originalEstimate"] = self.issue_json["fields"][
                "timetracking"
            ]["originalEstimateSeconds"]

        self.issue_progress["total"] = self.issue_json["fields"]["progress"]["total"]
        self.issue_progress["progress"] = self.issue_json["fields"]["progress"][
            "progress"
        ]
        self.issue_progress["progressPercent"] = 0
        if "percent" in self.issue_json["fields"]["progress"]:
            self.issue_progress["progressPercent"] = self.issue_json["fields"][
                "progress"
            ]["percent"]

        self.issue_progress["timeLeft"] = 0
        if self.issue_json["fields"]["timeestimate"] != None:
            self.issue_progress["timeLeft"] = self.issue_json["fields"]["timeestimate"]

        self.issue_aggregate_progress["originalEstimate"] = 0
        self.issue_aggregate_progress["total"] = 0
        self.issue_aggregate_progress["progress"] = 0
        self.issue_aggregate_progress["progressPercent"] = 0
        self.issue_aggregate_progress["timeLeft"] = 0

        if (
            self.issue_has_subtasks
            and self.issue_json["fields"]
            and self.issue_json["fields"]["aggregateprogress"]
        ):
            if (
                self.issue_json["fields"]
                and self.issue_json["fields"]["aggregatetimeoriginalestimate"]
            ):
                self.issue_aggregate_progress["originalEstimate"] = self.issue_json[
                    "fields"
                ]["aggregatetimeoriginalestimate"]

            self.issue_aggregate_progress["total"] = self.issue_json["fields"][
                "aggregateprogress"
            ]["total"]
            self.issue_aggregate_progress["progress"] = self.issue_json["fields"][
                "aggregateprogress"
            ]["progress"]

            if "percent" in self.issue_json["fields"]["aggregateprogress"]:
                self.issue_aggregate_progress["progressPercent"] = self.issue_json[
                    "fields"
                ]["aggregateprogress"]["percent"]

        if (not self.issue_has_subtasks
            and self.issue_json["fields"]
            and self.issue_json["fields"]["aggregateprogress"]
            and "total" in self.issue_json["fields"]["aggregateprogress"]
            ):
            self.issue_aggregate_progress["originalEstimate"] = self.issue_json["fields"]["aggregateprogress"]["total"]
            self.issue_aggregate_progress["progress"] = self.issue_json["fields"]["aggregateprogress"]["progress"]

        if (not self.issue_has_subtasks
            and self.issue_json["fields"]
            and self.issue_json["fields"]["progress"]
            and "total" in self.issue_json["fields"]["progress"]
            ):
            self.issue_progress["originalEstimate"] = self.issue_json["fields"]["progress"]["total"]
            self.issue_progress["progress"] = self.issue_json["fields"]["progress"]["progress"]

        if self.issue_json["fields"]["aggregatetimeestimate"] != None:
            self.issue_aggregate_progress["timeLeft"] = self.issue_json["fields"][
                "aggregatetimeestimate"
            ]

        self.issue_progress["timeLeftOriginal"] = 0
        if self.issue_progress["originalEstimate"] > 0:
            self.issue_progress["timeLeftOriginal"] = (
                self.issue_progress["originalEstimate"] - self.issue_progress["progress"]
            )

        self.issue_aggregate_progress["timeLeftOriginal"] = 0
        if self.issue_aggregate_progress["originalEstimate"] > 0:
            self.issue_aggregate_progress["timeLeftOriginal"] = (
                self.issue_aggregate_progress["originalEstimate"]
                - self.issue_aggregate_progress["progress"]
            )

    def get_parse_subtasks(self, logProgress: bool = True):
        self.subtasks_wo_estimation_count = 0
        self.subtasks_original_estimation = 0
        self.subtasks_wo_estimation = []

        i = 0
        if self.issue_has_subtasks:
            printLine = "Subtasks count: " + str(self.subtasks_count) + " "

            if logProgress:
                print("")
                print(printLine)

            for subtask in self.issue_json["fields"]["subtasks"]:

                if logProgress:
                    # sys.stdout.write('\\')
                    loader = "/"
                    if i == 1:
                        loader = "\\"
                        i = 0
                    else:
                        i = 1
                    print("\033[F" + printLine + loader)

                subtaskURL = self.jira_base_api_utl + subtask["key"]
                resp = requests.get(
                    subtaskURL,
                    auth=TokenAuth(self.auth_token),
                    params=self.request_params,
                )

                if resp.status_code != 200:
                    raise Exception(
                        "Issue {} details response code: {}".format(
                            subtask["key"], resp.status_code
                        )
                    )

                subtaskJson = resp.json()
                if "originalEstimate" not in subtaskJson["fields"]["timetracking"]:
                    self.subtasks_wo_estimation.append(subtask["key"])
                    if subtask["fields"]["status"]["name"] != "Done":
                        self.subtasks_wo_estimation_count += 1
                        # print(', ESTIMATION needed!')
                else:
                    if (
                        "originalEstimateSeconds"
                        in subtaskJson["fields"]["timetracking"]
                    ):
                        self.subtasks_original_estimation += subtaskJson["fields"][
                            "timetracking"
                        ]["originalEstimateSeconds"]
                        # print(', originalEstimate = ', self.convertMsToHours(subtaskJson['fields']['timetracking']['originalEstimateSeconds']))

        self.subtasks_original_estimation = self.convertMsToHours(
            self.subtasks_original_estimation
        )

    def convertMsToHours(self, valueMs: int, showUnit: bool = True) -> str:
        result = str(valueMs / 3600)
        if showUnit:
            result += "h"
        return result

    @staticmethod
    def form_jql_query(
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

    def print_general_info(self):
        print("Issue type:", self.issue_original_type_name)
        print("Are there subtasks?:", self.issue_has_subtasks)

        termColor = WARN_BG_COLOR
        if self.issue_status == "Done":
            termColor = GREEN_COLOR
        if self.issue_status == "To Do" or self.issue_status == "Open":
            termColor = BLUE_COLOR
        print(self.issue_type_name + " status:", termColor + self.issue_status + ENDTERM)

    def print_progress_info(self):
        if (
            self.issue_progress["total"] > 0
            or self.issue_progress["originalEstimate"] > 0
        ):
            print("")
            print("Exact " + self.issue_type_name.lower() + " progress:")
            print(
                " Original estimation = ",
                self.convertMsToHours(self.issue_progress["originalEstimate"]),
            )
            print(" Total:", self.convertMsToHours(self.issue_progress["total"]))
            print(" Progress:", self.convertMsToHours(self.issue_progress["progress"]))
            print(" ", str(self.issue_progress["progressPercent"]) + "%")
            timeLeftColor = GREEN_COLOR
            if self.issue_progress["timeLeft"] <= 0:
                timeLeftColor = RED_COLOR
            print(
                " Time left: ",
                timeLeftColor
                + self.convertMsToHours(self.issue_progress["timeLeft"])
                + ENDTERM,
            )
            timeLeftColor = GREEN_COLOR
            if self.issue_progress["timeLeftOriginal"] <= 0:
                timeLeftColor = RED_COLOR
            print(
                " Time left (original): ",
                timeLeftColor
                + self.convertMsToHours(self.issue_progress["timeLeftOriginal"])
                + ENDTERM,
            )

        if self.issue_aggregate_progress["total"] > 0 and self.issue_has_subtasks:
            print("")
            print("Aggregated progress:")
            print(
                " Original estimation = ",
                self.convertMsToHours(self.issue_aggregate_progress["originalEstimate"]),
            )
            print(
                " Total:", self.convertMsToHours(self.issue_aggregate_progress["total"])
            )
            print(
                " Progress:",
                self.convertMsToHours(self.issue_aggregate_progress["progress"]),
            )
            print(" ", str(self.issue_aggregate_progress["progressPercent"]) + "%")
            timeLeftColor = GREEN_COLOR
            if self.issue_aggregate_progress["timeLeft"] <= 0:
                timeLeftColor = RED_COLOR
            print(
                " Time left: ",
                timeLeftColor
                + self.convertMsToHours(self.issue_aggregate_progress["timeLeft"])
                + ENDTERM,
            )
            timeLeftColor = GREEN_COLOR
            if self.issue_aggregate_progress["timeLeftOriginal"] <= 0:
                timeLeftColor = RED_COLOR
            print(
                " Time left (original): ",
                timeLeftColor
                + self.convertMsToHours(self.issue_aggregate_progress["timeLeftOriginal"])
                + ENDTERM,
            )

    def get_compact_progress_info(self) -> str:
        originalInfoLine = ""
        if (
            self.issue_progress["total"] > 0
            or self.issue_progress["originalEstimate"] > 0
        ):
            estimation = self.issue_progress["originalEstimate"]

            originalColor = ""
            originalEndColor = ""

            if self.issue_progress["originalEstimate"] == 0:
                originalColor = RED_COLOR
                originalEndColor = ENDTERM

            originalInfoLine += (
                "Original: e"
                + originalColor
                + self.convertMsToHours(estimation)
                + originalEndColor
                + ", p"
            )
            totalColor = ""
            totalEndColor = ""
            if self.issue_progress["total"] > self.issue_progress["originalEstimate"]:
                totalColor = WARN_COLOR
                totalEndColor = ENDTERM
            originalInfoLine += (
                self.convertMsToHours(self.issue_progress["progress"], False)
                + "/"
                + totalColor
                + self.convertMsToHours(self.issue_progress["total"])
                + totalEndColor
            )
            originalInfoLine += ", " + str(self.issue_progress["progressPercent"]) + "%"
            timeLeftColor = GREEN_COLOR
            if self.issue_progress["timeLeft"] <= 0:
                timeLeftColor = RED_COLOR
            originalInfoLine += (
                ", l"
                + timeLeftColor
                + self.convertMsToHours(self.issue_progress["timeLeft"], False)
                + ENDTERM
            )
            timeLeftColor = GREEN_COLOR
            if self.issue_progress["timeLeftOriginal"] <= 0:
                timeLeftColor = RED_COLOR
            originalInfoLine += (
                ", lo"
                + timeLeftColor
                + self.convertMsToHours(self.issue_progress["timeLeftOriginal"])
                + ENDTERM
            )

        if self.issue_aggregate_progress["total"] > 0 and self.issue_has_subtasks:
            if len(originalInfoLine) > 0:
                originalInfoLine += "\r\n"
            originalInfoLine += (
                "Aggregated: e"
                + self.convertMsToHours(self.issue_aggregate_progress["originalEstimate"])
                + ", p"
            )
            totalColor = ""
            totalEndColor = ""
            if (
                self.issue_aggregate_progress["total"]
                > self.issue_aggregate_progress["originalEstimate"]
            ):
                totalColor = WARN_COLOR
                totalEndColor = ENDTERM
            originalInfoLine += (
                self.convertMsToHours(self.issue_aggregate_progress["progress"], False)
                + "/"
                + totalColor
                + self.convertMsToHours(self.issue_aggregate_progress["total"])
                + totalEndColor
            )
            originalInfoLine += (
                ", " + str(self.issue_aggregate_progress["progressPercent"]) + "%"
            )

            timeLeftColor = GREEN_COLOR
            if self.issue_aggregate_progress["timeLeft"] <= 0:
                timeLeftColor = RED_COLOR
            originalInfoLine += (
                ", l"
                + timeLeftColor
                + self.convertMsToHours(self.issue_aggregate_progress["timeLeft"], False)
                + ENDTERM
            )
            timeLeftColor = GREEN_COLOR
            if self.issue_aggregate_progress["timeLeftOriginal"] <= 0:
                timeLeftColor = RED_COLOR
            originalInfoLine += (
                ", lo"
                + timeLeftColor
                + self.convertMsToHours(self.issue_aggregate_progress["timeLeftOriginal"])
                + ENDTERM
            )

        return originalInfoLine

    def print_subtasks_stats(self):
        if self.issue_has_subtasks:
            print("")
            print("Sub-tasks initial estimation: ", self.subtasks_original_estimation)
            print("Sub-tasks with NO estimation: ", self.subtasks_wo_estimation_count)
