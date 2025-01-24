// openai handler
// See https://javascript.info/xmlhttprequest
// Hint: see https://api.openai.com/v1/models for all supported models

var contents;

/------------------------------------------------------------------------------/

function sendRequestToChatGPT(query) {

    console.log("Function sendRequestToChatGPT");

    console.log(`I received arg "${query}"`);
    const testCase = query.split(':')[1];
    console.log(`testCase is "${testCase}"`);

    if (typeof contents == 'undefined') {
        window.alert('Please load your JSON data first');
        return;
    }

    const apiKey = contents.OPENAI_API_KEY;
    const base_url = contents.OPENAI_BASE_URL;
    const model = contents.OPENAI_MODEL;

    // Check we have the API key
    if (! apiKey) {
        window.alert('Please load your OpenAI API key first');
        return false;
    }

    // Create the XMLHttpRequest object
    var xhr = new XMLHttpRequest();
    xhr.withCredentials = false;

    // Set the HTTP method and URL
    xhr.open("POST", base_url, true);

    console.log(`Key is "${apiKey}"`);
    // Set the request headers
    xhr.setRequestHeader("Authorization", "Bearer " + apiKey);
    xhr.setRequestHeader("Content-Type", "application/json");

    xhr.timeout = 30000;  // 30 second timeout
    xhr.ontimeout = function() { window.alert('No response from server.'); }

    // Set the response type
    xhr.responseType = "json";

    /--------------------------------------------------------------------------/
    // Create the body of the request string as JSON and
    // insert the testCase into the user content

    var request_body = `{
        "model": "${model}",
        "messages":
        [{
            "role": "system",
            "content": "You are a junos network operator"
         },
         {
            "role":"user",
            "content": "What are the best 3 suggestions to solve the error ${testCase}"
         }],
        "max_tokens": 400}`

    // Send the request
    xhr.send(request_body);
    console.log("Message sent");

    xhr.onprogress = function(event) {
        // report progress
        console.log(`Loaded ${event.loaded} bytes`);
    };

    // Handle the response
    xhr.onload = function() {

        const data = xhr.response;
        console.log(data.error.type + ": " + data.error.code + ": " + data.error.message);

        if (xhr.status != 200) {
            // The request failed
            window.alert("Request failed with status: " + xhr.status + ": " + data.error.message);
            return;
        }

        // Request succeeded. The response is JSON
        var response = xhr.response;
        console.log("Response received");
        console.log(response["choices"][0]["message"]["content"]);

        window.alert(response.choices[0].message.content);

    };

    xhr.onerror = function() {
        // handle non-HTTP error (e.g. network down)
        console.log (`Request failed with network error ${xhr.status}`);

        if (xhr.status == 0) {
            window.alert ("Failed to send request to API Server. Please retry with browser in developer mode.");
        }

    };

    return false;
}
