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

    // Check we have the API key
    if (typeof contents == 'undefined') {

        window.alert('Please load your OpenAI Key first');
        return;
    }

    // Create the XMLHttpRequest object
    var xhr = new XMLHttpRequest();
    xhr.withCredentials = false;

    const apiKey = contents.OPENAI_API_KEY;
    console.log(`The API key is ${apiKey}`);

    // Set the HTTP method and URL
    xhr.open("POST", "https://api.openai.com/v1/chat/completions", true);

    // Set the request headers
    xhr.setRequestHeader("Authorization", `Bearer ${apiKey}`);
    xhr.setRequestHeader("Content-Type", "application/json");

    // Set the response type
    xhr.responseType = "json";

    /--------------------------------------------------------------------------/
    // Create the body of the request string as JSON and
    // insert the testCase into the user content

    var request_body = `{
	"model": "gpt-3.5-turbo",
	"messages":
	[{
	    "role": "system",
	    "content": "You are a network operator"
	 },
	 {
	    "role":"user",
	    "content": "What are the best 3 suggestions to solve the error ${testCase}"
	 }],
	"max_tokens": 400}`

    // Send the request
    xhr.send(request_body);
    console.log("Message sent");

    // Handle the response
    xhr.onload = function() {

        if (xhr.status != 200) {
            // The request failed
            window.alert("Request failed. Status: " + xhr.status);
            return;
        }

        // Request succeeded. The response is JSON
        var response = xhr.response;
	console.log("Response received");
        console.log(response["choices"][0]["message"]["content"]);

	window.alert(response.choices[0].message.content);

    };

    xhr.onprogress = function(event) {
        // report progress
        console.log(`Loaded ${event.loaded} bytes`);
    };

    xhr.onerror = function() {
        // handle non-HTTP error (e.g. network down)
        window.alert(`Network error: ${xhr.status}`);
    };
 
    return false;
}
