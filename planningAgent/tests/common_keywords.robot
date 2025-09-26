***Settings***
Library    RequestsLibrary

***Keywords***
Create User Session
    [Arguments]    ${ALIAS}    ${URL}
    Create Session    ${ALIAS}    ${URL}    verify=True

Extract CSRF Token From Response
    [Documentation]    Extracts the 'csrftoken' value from the cookies of a Response object.
    [Arguments]    ${RESPONSE}
    # FIX: Use BuiltIn.Evaluate to directly access the cookie dictionary key from the response object
    ${CSRF_TOKEN}=    Evaluate    $RESPONSE.cookies.get('csrftoken')
    RETURN    ${CSRF_TOKEN}

Create Headers With CSRF
    [Arguments]    ${CSRF_TOKEN}
    ${HEADER}=    Create Dictionary    Content-Type=application/json    X-CSRFToken=${CSRF_TOKEN}
    RETURN    ${HEADER}
