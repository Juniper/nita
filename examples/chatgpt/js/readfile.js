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
    console.log(contents.OPENAI_API_KEY);

  };
  reader.readAsText(file);
}

document.getElementById('file-input')
  .addEventListener('change', readSingleFile, false);
