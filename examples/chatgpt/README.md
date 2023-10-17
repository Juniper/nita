# ChatGPT Integration with Robot via Jenkins

This example enhancement to NITA uses ChatGPT to help you figure out why certain test cases might have failed and what you can do to fix them. This can be incredibly useful for level 1 network operations staff, who might need an artificial assistant to help them investigate why a test may have failed. Note that you (or whoever runs the query) will need [an account with OpenAI](https://platform.openai.com/signup?launch) for all of this to work.

## Overview

What we will do is modify the results page of Robot tests which Jenkins serves to us. Jenkins will summarise the failed test results at the top of the page, so all we need to do is add a way to pass the test case description to ChatGPT. For this to work we need to add two new artifacts to the Jenkins UI, one is a button that we can use to upload an API key (for OpenAI) and the other is a hyperlink that we can use to trigger a call to ChatGPT. These two new artifacts will make the results page look like this:

![New artifacts on the Robot results page](images/img1.JPG)

Follow the steps described in this README to install and edit the files necessary to make this work...

## Step 1: The Robot Plugin Jar File

You'll need to edit the Robot Java Archive ("jar") file to change one of the jelly files inside it. Start by making a copy of the original jar file, then extract the archive, edit it, re-create a new one and copy that back in place of the original. Follow these steps:

### Copy the original Jar

From the NITA host machine, you'll need to work inside the Jenkins container as the root user, like this:

```shell
$ nita-cmd jenkins cli root
# cd /var/jenkins_home/plugins/robot/WEB-INF/lib
# cp robot.jar robot.jar.original
```

:warning: Should things go wrong, you can always rollback to that. Now continue by extracting the jar file:

```shell
# cp robot.jar ~
# cd
# jar xf robot.jar
```

This will extract three things, a file called `index.jelly`, a directory called `META-INF` and another directory called `hudson`. This last one is the one that we will work in.

### Edit the failedCases template

Edit the file ``hudson/plugins/robot/util/failedCases.jelly`` and make the following changes:

Just below the `<h2>` heading, add a line that will input (read) a file into the name `file-input`, with a line like this:

```<p>Upload OpenAI Key: <input type="file" id="file-input"/></p>```

Add a line to create a new HTML table column called something like "Action", like this:

```<td class="pane-header" style="text-align:center;" title="Action">Action</td>```

Add a line to send the Robot test case name to the ChatGPT JavaScript function when it is clicked, like this:

```<td class="pane" style="text-align:center;"><a href="#" onclick="javascript:sendRequestToChatGPT(&quot;${case.name}&quot;)">Ask ChatGPT</a></td>```

And add a couple of lines after the end of the HTML table that loads in some JavaScript, like this:

```
        <script src="${rootURL}/userContent/js/readfile.js"></script>
        <script src="${rootURL}/userContent/js/openai.js"></script>
```
With those changes made, the whole file `failedCases.jelly` should look something like this:

``` xml
<?xml version="1.0" encoding="UTF-8"?>
<?jelly escape-by-default='true'?>
<j:jelly xmlns:j="jelly:core" xmlns:st="jelly:stapler" xmlns:d="jelly:define" xmlns:l="/lib/layout" xmlns:t="/lib/hudson" xmlns:f="/lib/form" xmlns:u="/util">
    <j:if test="${!it.allFailedCases.isEmpty()}">
        <style>
            td.pane {
                vertical-align: top;
            }
        </style>
        <h2>Failed Test Cases</h2>
        <p>Upload OpenAI Key: <input type="file" id="file-input"/></p>
        <table class="pane sortable">
            <tr>
                <td class="pane-header" title="Test case name. Click to sort.">Name</td>
                <td class="pane-header" style="text-align:center !important;" title="Criticality. Click to sort.">Crit.</td>
                <td class="pane-header" title="Duration. Click to sort.">Duration</td>
                <td class="pane-header" style="text-align:center;" title="Number of failed builds. Click to sort.">Age</td>
                <td class="pane-header" style="text-align:center;" title="Action">Action</td>
            </tr>
            <j:forEach var="case" items="${it.allFailedCases}">
                <j:set var="fullName" value="${case.getRelativePackageName(it)}" />
                <tr>
                    <td class="pane">
                        <a id="${h.escape(fullName)}-showlink" href="javascript:showStackTrace('${h.jsStringEscape(h.escape(fullName))}','${h.jsStringEscape(case.getRelativeId(it))}/summa
ry')" class="expand"></a>
                        <a id="${h.escape(fullName)}-hidelink" style="display:none" href="javascript:hideStackTrace('${h.jsStringEscape(h.escape(fullName))}')" class="collapse"></a>
                        <st:nbsp/>
                        <a href="${case.getRelativeId(it)}"><small>${case.getRelativeParent(it)}</small>${case.name}</a>
                        <div id="${h.escape(fullName)}" class="hidden" style="display:none">
                            ${%Loading...}
                        </div>
                    </td>
                    <td class="pane" style="text-align:center;"><j:if test="${case.isCritical()}">yes</j:if><j:if test="${!case.isCritical()}">no</j:if></td>
                    <td class="pane">${case.humanReadableDuration}</td>
                    <td class="pane" style="text-align:center;"><a href="${rootURL}/${case.failedSinceRun.url}">${case.age}</a></td>
                    <td class="pane" style="text-align:center;"><a href="#" onclick="javascript:sendRequestToChatGPT(&quot;${case.name}&quot;)">Ask ChatGPT</a></td>
                </tr>
            </j:forEach>
        </table>
        <script src="${rootURL}/userContent/js/readfile.js"></script>
        <script src="${rootURL}/userContent/js/openai.js"></script>
    </j:if>
</j:jelly>
```
There is an example ![failedCases.jelly](failedCases.jelly) file in this repo, should you want to use it.

### Create a new Jar File

Next, create a new jar file that includes your changed file, and put it back in the right place, like this:

```
# cd
# rm robot.jar
# jar cf robot.jar index.jelly META-INF/ hudson/
# cp robot.jar /var/jenkins_home/plugins/robot/WEB-INF/lib
# chown jenkins:jenkins /var/jenkins_home/plugins/robot/WEB-INF/lib/robot.jar
```
## Step 2: Edit the Jenkins Start Script

Jenkins was hardened several years ago to prevent people making malicious changes to it (see https://www.jenkins.io/redirect/class-filter/ for details), and so without adding specific classes to a whitelist your changes will be rejected when Jenkins next runs. You need to provide a whitelist of Robot classes as options to the Java executable, by adding the following line to the startup script `/usr/local/bin/jenkins.sh` that lives in the Jenkins container, like this:

```
java_opts_array+=( "-Dhudson.remoting.ClassFilter=hudson.plugins.robot.RobotPublisher,hudson.plugins.robot.model.RobotSuiteResult,hudson.plugins.robot.model.RobotCaseResult,hudson.plugins.robot.util.failedCases,hudson.plugins.robot.model.RobotResult,hudson.plugins.robot.RobotBuildAction")
```
Add this new line just below the "fi" closing if-statement on line 26. There is an example ![jenkins.sh](jenkins.sh) file in this repo, if you wish to use it. Now you can `exit` from the Jenkins container.

## Step 3: Copy Example JavaScript Files

:bulb: Pro-Tip: The directory `/var/nita_project` on the host maps to `/project` in the Jenkins container, making it easy to move files between the host and the container.

Download the example JavaScript files provided in this repository (![readfile.js](js/readfile.js) and ![openai.js](js/openai.js)) and save them on the NITA host machine in the `/var/nita_project` directory. Then, in the Jenkins container, create a directory `/var/jenkins_home/userContent/js` and copy them across. Like this:

```
$ cd /var/nita_project
$ wget https://raw.githubusercontent.com/Juniper/nita/main/examples/chatgpt/js/openai.js
$ wget https://raw.githubusercontent.com/Juniper/nita/main/examples/chatgpt/js/readfile.js
$ nita-cmd jenkins cli jenkins
$ mkdir /var/jenkins_home/userContent/js
$ mv /project/openai.js /var/jenkins_home/userContent/js
$ mv /project/readfile.js /var/jenkins_home/userContent/js
$ exit
```

You can either use the example Javascript files provided, or create your own, but they must go in the directory `/var/jenkins_home/userContent/js` that matches the `<script src>` lines that you added to the jelly file above.

:warning: Note that the ![openai.js](js/openai.js) script permits a maximum of 400 tokens to be used in the exchange with ChatGPT, but you might want to adjust this to suite your needs and budget. Tokens are the currency used by the OpenAI API which you need to pay for - if you don't know what a token is, or how much it costs, check out the latest [OpenAI pricing page](https://openai.com/pricing).

## Step 4: Restart Jenkins

That's it, there are no more changes to make. From the nita host just restart the Jenkins container:

```
$ nita-cmd jenkins restart
$ nita-cmd jenkins logs
```

## Step 5: Test It

Check for errors in the log as you access a page such as `https://<jenkins>:<port>/job/<test>/lastBuild/robot/#`. The next thing to do is to upload your OpenAI API Key, which you do by pressing the `Browse...` button that is now on the page. The key file must be JSON formatted, with at least one entry like this:

``` js
{
"OPENAI_API_KEY": "sk-xxxxxxxxxxxxxx"
}
```
The "xxxx" should be replaced with your actual OpenAI API key (there is an example ![key.json](key.json) file in this repo, which you can use as a template to edit). Then simply click on an "Ask ChatGPT" link alongside any particular failed test case that you want help with. Expect a delay of between 5-10 seconds whilst ChatGPT does its thing, and then a window will appear with some helpful suggestions, a bit like this:

![Example output image](images/img2.JPG)

And if nothing appears to be working, press `F12` in your browser to review the console output. Otherwise kick back, relax and admire your work. Well done!
