# AI Integration with Robot via Jenkins

This example enhancement to NITA uses an AI such as ChatGPT to help you figure out why certain test cases might have failed and what you can do to fix them. This can be incredibly useful for level 1 network operations staff, who might need an artificial assistant to help them investigate why a test may have failed. Note that you (or whoever runs the query) will also need an account with the AI 
[such as ChatGPT](https://platform.openai.com/signup?launch) for all of this to work.

## Overview

What we will do is modify the results page of Robot tests which Jenkins serves to us. Jenkins will summarise the failed test results at the top of the page, so all we need to do is add a way to pass the test case description to an AI. For this to work we need to add two new artifacts to the Jenkins UI, one is a button that we can use to upload an API key, URL and AI model to use, and the other is a hyperlink that we can use to trigger a call to the AI server. These two new artifacts will make the results page look like this:

![New artifacts on the Robot results page](images/img1.JPG)

Follow the steps described in this README to install and edit the files necessary to make this work...

## Step 1: Build a Custom Jenkins Container

Refer to the [Creating Custom Containers](https://github.com/Juniper/nita/blob/main/docs/custom-containers.md) document for details on how to create a custom Jenkins container for NITA. You should use the [Dockerfile](./Dockerfile) in this repo to easily build your own container. It will copy the customised ![jenkins.sh](jenkins.sh) script into the new container, which will allow the Jenkins Java runtime to execute our customised ![robot.jar](https://raw.githubusercontent.com/Juniper/nita/main/examples/chatgpt/robot.jar) file.

## Step 2: Get Persistent Files

:bulb: Pro-Tip: The directory `/mnt/data` on the NITA host is used by Kubernetes as a "persistent volume" for the Jenkins pod, and it maps to `/var/jenkins_home` in the Jenkins container.

This means that files stored under `/mnt/data` on the host are always accessible to the Jenkins container inside the Jenkins pod, and the files held therein persists through restarts of the pod. It also means that files stored under `/mnt/data` on the host take precedent (and overwrite) files stored there by the container. In a nutshell, if you want Jenkins to have access to files persistently, the way to do that is to store them under `/mnt/data` on the NITA host. We'll do this now...

### Robot.jar File

The `robot.jar` file is a Java Archive that has been customised to use a modified `failedCases.jelly` file. The modifications made to this file include new HTML to provide the artifacts described above (a button to load your API key, and links to custom JavaScript inside the "Failed Cases" table). You will need to download the `robot.jar` file from this repo and copy it to the appropriate directory as shown here:

```
$ wget https://raw.githubusercontent.com/Juniper/nita/main/examples/chatgpt/robot.jar
$ sudo cp robot.jar /mnt/data/plugins/robot/WEB-INF/lib
```
:exclamation: Note that `/mnt/data/plugins/robot/WEB-INF/lib` on the NITA host maps to `/var/jenkins_home/plugins/robot/WEB-INF/lib` in the Jenkins container.

### Copy JavaScript Files

On the NITA host machine create a directory for JavaScript files under `/mnt/data/userContent/js`. Files placed here will be accessible to the Jenkins UI. Then download the JavaScript files provided in this repository (![readfile.js](js/readfile.js) and ![openai.js](js/openai.js)) and copy them across, like this:

```
$ wget https://raw.githubusercontent.com/Juniper/nita/main/examples/chatgpt/js/openai.js
$ wget https://raw.githubusercontent.com/Juniper/nita/main/examples/chatgpt/js/readfile.js
$ sudo mkdir -p /mnt/data/userContent/js
$ sudo cp openai.js /mnt/data/userConent/js
$ sudo cp readfile.js /mnt/data/userContent/js
```

You can either use the example Javascript files provided in this repo or create your own, but they must go in the `/mnt/data/userContent/js` directory to be accessible to the Jenkins container.

:warning: Note that the ![openai.js](js/openai.js) script permits a maximum of 400 tokens to be used in the exchange with AI, but you might want to adjust this to suit your needs and budget. Tokens are the currency commonly used by AI such as ChatGPT which you need to pay for - if you don't know what a token is, or how much it costs, check out the latest [OpenAI pricing page](https://openai.com/pricing) (for example).

## Step 3: Test It

Check for errors in the log as you access a page such as `https://<jenkins>:<port>/job/<test>/lastBuild/robot/#`. The next thing to do is to upload your API Key, URL and model in a file, which you do by pressing the `Browse...` button that is now on the page. The file must be JSON formatted, with the following fields like this:

``` js
{
  "OPENAI_API_KEY": "sk-xxxxxxxxxxxxxx",
  "OPENAI_BASE_URL": "https://<api url>",
  "OPENAI_MODEL": "<api model>"
}
```
If you don't know which URL or model to use you can leave them blank and NITA will default to using the following values for ChatGPT:

Object Name | Description
---|---
``OPENAI_API_KEY`` |  The API key. This is required, so if it is not provided the script will return ``false`` (i.e. fail to continue)
``OPENAI_BASE_URL`` | The URL of the API server. If this is not provided, the script will default to using ``https://api.openai.com/v1/chat/completions`` (ChatGPT)
``OPENAI_MODEL`` | The name of the Large Language Model to use. If this is not provided, the script will default to using ``gpt-3.5-turbo``


The key is required and the "xxxx" in the example above should be replaced with your actual API key! There is an example ![key.json](key.json) file in this repo, which you can use as a template to edit. Then simply click on an "Ask AI" link alongside any particular failed test case that you want help with. Expect a delay of between 5-10 seconds whilst ChatGPT does its thing, and then a window will appear with some helpful suggestions, a bit like this:

![Example output image](images/img2.JPG)

And if nothing appears to be working, press `F12` in your browser to review the console output. Otherwise kick back, relax and admire your work. Well done!

## :warning: Cross Origin Resource Sharing

Note that the [openai.js](../openai/openai.js) script uses the ``XMLHttpRequest()`` JavaScript method to construct an API request that is sent to the server. Before sending an ``HTTP POST`` request, this method will send an ``OPTIONS`` request to the server first to verify that the server will allow the client to set the ``Authorization`` and ``Content-type`` fields in the header. This is standard industry practice, called "Cross-Origin Resource Sharing (CORS)" (see [mozilla.org](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS) and [Stack Overflow](https://stackoverflow.com/questions/15605823/why-is-httprequest-sending-the-options-verb-instead-of-post#15605935) for descriptions). However, for this to succeed, the remote API server must be configured to allow these fields to be set in the header. For example, if the API server is an Apache server, the following 3 lines must be included in the server configuration:

```bash
Header set Access-Control-Allow-Origin "*"
Header set Access-Control-Allow-Methods "GET,POST,OPTIONS"
Header set Access-Control-Allow-Headers "Authorization, Content-Type, Origin"
```
If the code fails during testing, and the browser console reports CORS errors, you will need to contact the administrators of the remote server and ask them to configure the CORS settings described here.
