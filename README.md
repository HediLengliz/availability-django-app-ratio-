Planning Agent API Tests 🤖
This repository contains API integration tests for the Planning Agent application, built using Robot Framework and the RequestsLibrary.

🚀 Getting Started
These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

Prerequisites
You need Python (3.7+) installed to run Robot Framework.

Robot Framework

RequestsLibrary (for HTTP/API testing)

Install the necessary libraries using pip:

Bash

pip install robotframework robotframework-requests
Configuration
The tests assume the API server is running locally on the default address.

Base URL: http://localhost:8000/swagger

If your API is running on a different port or server, update the ${BASE_URL} variable in api_use_cases.robot.

📂 Project Structure
File	Description
api_use_cases.robot	The main test suite containing sequential API workflow tests (Registration, Login, CRUD, Reporting).
common_keywords.robot	Contains reusable keywords like session creation and utility functions (e.g., CSRF token handling).
README.md	This file.
/results	(Generated folder) Contains test reports and logs after execution.

Export to Sheets
▶️ How to Run Tests
Execute the test suite from your terminal in the project's root directory:

Bash

robot api_use_cases.robot
Viewing Results
After the run, three output files will be generated:

output.xml (Raw results data)

log.html (Detailed execution log—essential for debugging failures)

report.html (High-level summary of test status)

Open report.html in your web browser to view the final results.

🛠️ Key Test Workflows
The api_use_cases.robot suite executes the following end-to-end scenarios:

User Registration (TUC 1): Creates a new unique user.

Local User Login (TUC 2): Logs in the newly created user and establishes a session.

Create Calendar Entry (TUC 3): Adds a new calendar event for the logged-in user (CRUD Create).

Calculate Availability Report (TUC 4): Calculates and generates an availability report for the user based on their calendar.

Export Report as CSV (TUC 5): Exports the generated report in CSV format.

Export Report as PDF (TUC 6): Exports the generated report in PDF format.

⚠️ Troubleshooting Common Issues
Issue	Cause	Fix
ConnectionError	The API server is not running or is on the wrong URL/port.	Ensure the server is running and check ${BASE_URL} in api_use_cases.robot.
403 Forbidden	Missing CSRF Token on a POST/PUT request.	Ensure Extract CSRF Token From Response and Set Suite Variable ${CSRF_HEADER} in TUC 2 are working correctly.
404 Not Found	Incorrect URL path or missing dynamic variable.	Check the variable scope. If a variable is set in one test and used in another (e.g., ${REPORT_ID}), it must be set using Set Suite Variable.
Variable '${X}' not found	The variable was not defined or failed to be set in a previous step.	Review the log.html file to trace the execution path that sets the missing variable.
