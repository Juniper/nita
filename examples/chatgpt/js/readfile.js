// Read a file from the client

var contents;

function readSingleFile(fileobject) {

  var file = fileobject.target.files[0];

  if (!file) {
    return;
  }

  var reader = new FileReader();

  reader.onload = function(fileobject) {
    // We want a JSON file
    contents = JSON.parse(fileobject.target.result);
    console.log(contents);
	  
    if (! contents.OPENAI_BASE_URL) {
      console.log("Warning: OPENAI_BASE_URL was undefined. Setting to default.");
      contents.OPENAI_BASE_URL = "https://api.openai.com/v1/chat/completions";
    }
    console.log("OPENAI_BASE_URL is: " + contents.OPENAI_BASE_URL);

    if (! contents.OPENAI_MODEL) {
      console.log("Warning: OPENAI_MODEL was underfined. Setting to default.");
      contents.OPENAI_MODEL = "gpt-3.5-turbo";
    }
    console.log("OPENAI_MODEL is: " + contents.OPENAI_MODEL);

    if (! contents.OPENAI_API_KEY) {
      console.log("Warning: API Key is empty");
      window.alert('Did not find an OPENAI_API_KEY value in the input file.');
      return false;
    } else {
      console.log("OPENAI_API_KEY is: " + contents.OPENAI_API_KEY);
    }

  };
  reader.readAsText(file);
}

document.getElementById('file-input')
  .addEventListener('change', readSingleFile, false);
