***Settings***
Library    RequestsLibrary
Library    Collections
Library    String
Resource   common_keywords.robot

***Variables***
${BASE_URL}     http://127.0.0.1:8000/api/v1
${SESSION_ALIAS}    planning_session
${REPORT_ID}
${TODAY_DATE}   2025-10-06
${TEST_PASS}    ApiTestPass123

***Test Cases***

Test Use Case 1: User Registration and Profile Creation
    ${RANDOM_ID}=    Generate Random String    8    [NUMBERS][LOWER]
    ${TEST_USER}=    Set Variable    testuser_${RANDOM_ID}
    ${TEST_EMAIL}=   Set Variable    test_${RANDOM_ID}@robot.com
    Create User Session    ${SESSION_ALIAS}    ${BASE_URL}
    ${HEADER}=    Create Dictionary    Content-Type=application/json
    ${PAYLOAD}=    Create Dictionary    username=${TEST_USER}    email=${TEST_EMAIL}    password=${TEST_PASS}    first_name=Robot    last_name=Tester
    ${RESPONSE}=    POST On Session    ${SESSION_ALIAS}    /auth/register/    json=${PAYLOAD}    headers=${HEADER}
    Should Be Equal As Strings    ${RESPONSE.status_code}    201
    Dictionary Should Contain Key    ${RESPONSE.json()}    id
    Set Suite Variable    ${TEST_USER}    ${TEST_USER}
    Set Suite Variable    ${TEST_EMAIL}   ${TEST_EMAIL}
    Set Suite Variable    ${TEST_PASS}    ${TEST_PASS}
    Set Suite Variable    ${TEST_FIRST_NAME}    Robot
    Set Suite Variable    ${TEST_LAST_NAME}     Tester

Test Use Case 2: Local User Login
      ${HEADER}=    Create Dictionary    Content-Type=application/json
        ${PAYLOAD}=    Create Dictionary    username=${TEST_USER}    password=${TEST_PASS}
        ${RESPONSE}=    POST On Session    ${SESSION_ALIAS}    /auth/login/    json=${PAYLOAD}    headers=${HEADER}
        Should Be Equal As Strings    ${RESPONSE.status_code}    200
        Dictionary Should Contain Key    ${RESPONSE.json()}    message

        # FIX A: Use the new, working keyword to extract CSRF token from the login response
        ${CSRF_TOKEN}=    Extract CSRF Token From Response    ${RESPONSE}
        ${CSRF_HEADER}=    Create Headers With CSRF    ${CSRF_TOKEN}

        # FIX B: Set the CSRF header as a Suite Variable for use in subsequent POST tests (TUC 3 & 4)
        Set Suite Variable    ${CSRF_HEADER}    ${CSRF_HEADER}

        # Verification: Access the protected /profile/ endpoint using the established session cookie
        ${RESPONSE}=    GET On Session    ${SESSION_ALIAS}    /profile/    headers=${HEADER}
        Should Be Equal As Strings    ${RESPONSE.status_code}    200
        Should Be Equal As Strings    ${RESPONSE.json()['username']}    ${TEST_USER}
        Should Be Equal As Strings    ${RESPONSE.json()['email']}    ${TEST_EMAIL}

Test Use Case 3: Create Calendar Entry (CRUD C)
    # FIX C: Use the CSRF_HEADER instead of a simple JSON header
    ${PAYLOAD}=    Create Dictionary    category=MEET    title=Weekly Standup    start_time=${TODAY_DATE}T10:00:00Z    end_time=${TODAY_DATE}T11:00:00Z
    ${RESPONSE}=    POST On Session    ${SESSION_ALIAS}    /calendar/    json=${PAYLOAD}    headers=${CSRF_HEADER}
    Should Be Equal As Strings    ${RESPONSE.status_code}    201
    Dictionary Should Contain Key    ${RESPONSE.json()}    id

Test Use Case 4: Calculate Availability Report
    ${PAYLOAD}=    Create Dictionary    date=${TODAY_DATE}
    ${RESPONSE}=    POST On Session    ${SESSION_ALIAS}    /availability/calculate/    json=${PAYLOAD}    headers=${CSRF_HEADER}
    Should Be Equal As Strings    ${RESPONSE.status_code}    201
    # FIX: Change 'Set Test Variable' to 'Set Suite Variable' to make REPORT_ID available to TUC 5 and 6.
    Set Suite Variable    ${REPORT_ID}    ${RESPONSE.json()['id']}
    Should Be True    ${RESPONSE.json()['total_available_hours']} < 168.0

Test Use Case 5: Export Report as CSV
    ${RESPONSE}=    GET On Session    ${SESSION_ALIAS}    /availability/${REPORT_ID}/export-csv/
    Should Be Equal As Strings    ${RESPONSE.status_code}    200
    # FIX: Check the 'Content-Type' header value directly
    BuiltIn . Should Be Equal As Strings    ${RESPONSE.headers['Content-Type']}    text/csv

Test Use Case 6: Export Report as PDF
    # FIX: Remove the extraneous '' from the URL path
    ${RESPONSE}=    GET On Session    ${SESSION_ALIAS}    /availability/${REPORT_ID}/export-pdf/
    Should Be Equal As Strings    ${RESPONSE.status_code}    200
    # FIX: Check the 'Content-Type' header value directly
    BuiltIn . Should Be Equal As Strings    ${RESPONSE.headers['Content-Type']}    application/pdf