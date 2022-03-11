# NAME

``nita-cmd`` Everything you need to know to drive NITA from its command line.

# SYNOPSIS

``nita-cmd``\
``nita-cmd help``\
``nita-cmd [script] [arguments]``

# DESCRIPTION

nita-cmd is a very simple bash shell based command line interface for controlling the components within NITA. It is provided as part of the nita-webapp container but could easily be copied to other systems or containers if you wish. It is also easily extensible, allowing a user to add new commands if they wish, and can even be used as a framework for creating simple command line interfaces for other non-NITA tools too.\

Note that ``nita-cmd`` replaces ``nita-cli``, an earlier python based command line interface which was provided with NITA prior to version 20.10.

## Interactive Mode

Without any arguments, simply typing ``nita-cmd`` on its own will take you into its interactive mode, for example:

```
$ nita-cmd
nita-cmd> help

    nita-cmd ansible cli 21.7 => Starts an ansible container (version 21.7) command line shell interface in the /project directory.
    nita-cmd cli version => Shows NITA CLI current version.
    nita-cmd containers ls => Lists all running NITA containers.
    nita-cmd containers versions => Lists all running NITA containers versions.
    nita-cmd images ls => Lists all NITA images.
    ...
 ```
Typing ``exit`` on its own will take you out of interactive mode and back to the parent shell.

## Executing Scripts

With the exception of the ``help`` argument, every argument that is passed to ``nita-cmd`` is an executable bash script that is stored in the directory ``/usr/local/bin``. When you type ``nita-cmd`` followed by an argument, it will look in that directory for the appropriate script and then execute it. The following "top-level" script arguments are currently supported by default:

```
$ nita-cmd ansible
$ nita-cmd cli
$ nita-cmd containers
$ nita-cmd images
$ nita-cmd ips
$ nita-cmd jenkins
$ nita-cmd license
$ nita-cmd robot
$ nita-cmd stats
$ nita-cmd webapp
```

To see the full list of supported arguments (i.e. scripts), just type ``nita-cmd help``. For details about what arguments are supported by each script, type the top-level script argument followed by ``help``, like this:

```
$ nita-cmd containers help
    nita-cmd containers ls => Lists all running NITA containers.
    nita-cmd containers versions => Lists all running NITA containers versions.
```

This example shows that it is possible to see the list of all running Docker containers and the versions of all of those containers. Typing ``nita-cmd containers list`` is much easier than having to remember the full Docker command that you need to type!

# CREATING YOUR OWN COMMAND

Because the ``nita-cmd`` script is actually a wrapper for executing other scripts, its functionality can easily be extended just be adding new scripts for it to execute. You do this by prefixing the name of your new executable shell script with ``nita-cmd_`` and storing it in the directory ``/usr/local/bin``. You can also add multiple levels to the command simply by creating multiple scripts with underscores between each argument in the filename.

## Hello World Example

Let's create a new command to print out "Hello World!". We will call this command "hello" and create it so that it can be run from nita-cmd by typing ``nita-cmd hello``. We begin by creating a new shell script that we will call ``nita-cmd_hello`` and this must go into the directory ``/usr/local/bin``. This script will be executed by ``nita-cmd`` whenever it is run with the top-level argument of ``hello``.

Given that ``/usr/local/bin`` is owned by root, we will need sudo access in order to create a new script there. The following steps can be used to create the example file to print out the line "Hello World!", and make it executable:

```shell
$ pwd
/usr/local/bin
$ sudo vi nita-cmd_hello
[sudo] password for jcluser: 
$ cat nita-cmd_hello
#!/bin/bash
if [ "$_CLI_RUNNER_DEBUG" == 1 ]; then
        echo `cat <<-EOT
echo "Hello World!"
EOT` >&2
fi
# This is the actual command that you want to wrap with the cli...
echo "Hello World!" >&1
$ sudo chmod +x nita-cmd_hello
$ 
```
Add inline debug by checking for the environment variable _CLI_RUNNER_DEBUG.
export _CLI_RUNNER_DEBUG=1

## Hello World Help Command

At the same time as you create a new command, you should also add a corresponding help script. You can do this by creating a script with the same filename as the new ``nita-cmd_`` script that you created, but suffixed with the word ``_help`` at the end. The convention here is just to have a simple script which outputs usage instructions to STDOUT, like this example below:

```shell
$ pwd
/usr/local/bin
$ sudo vi nita-cmd_hello_help
[sudo] password for jcluser: 
$ cat nita-cmd_hello_help
#!/bin/bash
echo -n "    nita-cmd hello => "
echo `cat <<-EOT
Outputs the classic Hello World statement
EOT` >&1
```

Now when you type ``help`` for your new command, you will see the help message:

```shell
$ nita-cmd hello help
Outputs the classic Hello World statement
$
```

# AUTO COMPLETION

Bash auto-complete is a really useful feature of the bash shell that allows a user to press the &lt;tab&gt; key in order to see valid input options or to have the shell automatically complete options that have already been partially typed in. On most systems, the configuration for auto-complete lives under ``/etc/bash_completion.d`` and does not need editing. In the case of ``nita-cmd``, the auto-complete configuation is provided for you and in order to reference it, the Unix user only needs to include the following statement in their local ``${HOME}/.bashrc`` file, thus:

```shell
if [ -f /usr/share/bash-completion/bash_completion ]; then
    . /usr/share/bash-completion/bash_completion
fi
```

Sourcing that file after editing it, or starting a new shell, will let the shell read the auto-complete configuration and from that point on, it will work. Try typing a partial command to check this is the case:

```shell
$ nita-cmd j<tab>
nita-cmd jenkins
$
```
And if you press &lt;tab&gt; again...

```shell
$ nita-cmd jenkins <tab>
backup   down     jobs     logs     ports    restore  start    stop     version  whoami   
cli      ips      labels   plugins  restart  set      status   up       volumes 
```
You get the idea.

# VERSION

To see which version of NITA you are running, type the command ``nita-cmd cli version`` like this:

```shell
$ nita-cmd cli version
nita-cli 21.7
$ 
```

# SEE ALSO

[nita-webapp](https://github.com/Juniper/nita-webapp)

[nita-cli](https://github.com/Juniper/nita-cli)
