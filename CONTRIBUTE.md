# CONTRIBUTE

## Why Contribute?

Hopefully you don't like reinventing the wheel, and you can see the benefit of using a solution that has already been developed by someone else, rather than developing it yourself. Using code that has already been developed and tested allows you to get up-and-running faster than if you had to figure out how to do it all by yourself. That added saving should allow you to continue the good work and eventually add your own parts to the solution that solve your own use cases. 

Once you have added and tested your part, the decent thing to do is to contribute it back to the community. This generous act of altruism will allow the next generation of users to benefit from your work, just like you benefitted from the work done by your forebears. 

This document explains the general process that you should follow when contributing your work.

## Stage 1

This first stage needs only to be done once, and should only take several minutes. Once you have followed the steps in this stage, you can move onto the second stage and skip this first stage altogether in the future.

### Create a GitHub.com Account

This sounds obvious, but if you want to contribute code to GitHub.com you will need to create an account here first. What might not be so obvious is that if you only ever want to take code from GitHub.com then you don't need an account. But no doubt you will want to contribute your work back to the community, so why not go ahead and create an account now. You can use your personal email address as your primary email address when you register, and GitHub.com will use this to send you account-related notifications. But you may also benefit from adding a work email address too, as explained in the next step.

### Verify your Email Address

Quite often, a project hosted on GitHub.com by an organization such as Juniper will allow contributions from two sources, employees and non-employees. We can tell if a contribution has come from an employee if their GitHub.com account has been verified against their corporate email address.

Please follow [the instructions here](https://docs.github.com/en/get-started/signing-up-for-github/verifying-your-email-address)

### Generate Keys

Now generate a public & private keypair in your development environment from [the steps outlined here](https://docs.github.com/en/authentication/managing-commit-signature-verification/generating-a-new-gpg-key). Note that you may need to install some dependencies into your development environment first, such as ```gnugpg``` and ```rng-tools```.

If you set a passphrase *keep it secure* and remember that you will need it whenever you sign a commit.

### Update Your Git Profile

Now that you have a GPG keypair you will need to update your GitHub.com account settings and add them. [Follow the instructions on GitHub](https://docs.github.com/en/authentication/managing-commit-signature-verification/adding-a-gpg-key-to-your-github-account) to do this. You should also update your local Git profile (in your development environment) and set your signing key and path to the GPG binary. It will be best if you use the ```git config --global``` command to set these values permanently, and you can find out details on [how to do that here](https://docs.github.com/en/authentication/managing-commit-signature-verification/telling-git-about-your-signing-key#telling-git-about-your-gpg-key-1)

## Stage 2

### Fork from Upstream

OK, now for the fun stuff. Obviously this step will vary depending upon what repository you want to contribute to, but the process is the same: find a repository on GitHub.com and click the "Fork" button. Most of the time you will only want to copy the ```master``` (aka ```main```) branch, so check that option is set and then press the Create Fork button. This will create a copy of the upstream repository in your personal GitHub.com account.

### Clone to a Development Environment

Most likely you are developing on a separate remote system and so you will need to get the code that you just forked sent from your GitHub.com account to the Git server on your development system. You do this by running the ```git clone``` command on your development system - see [the link here](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository) for more details. Moving files to and from GitHub.com will be much easier if you configure a Personal Access Token, or PAT, as this negates the need to send passwords between systems. Probably a fine-grained Personal Access Token is safest, as this allows you to control access to a specific repository for a limited time period. See the [link here](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token) for details on how to set up a PAT.

### Create a Branch

On your development system you should create a branch (a separate copy of the repository) where you can add your code. A good practice is to simply call this branch "development". You can do this with the Git command ```git checkout -b development```

### Add Your Work

Now make your changes on files or add new stuff into the development branch. Remember that you will need to run ```git add``` to any new file that did not originally exist.

## Stage 3

### Commit Locally

How often should you commit changes to your Git server? Wow, that is a philosophical question! Rather than committing every time you change a line of code, you should instead try to group up all of the small changes that are related together into one commit, and only you know when that makes sense. For example, if you are fixing a bug and change ten lines of code in two files that could be one commit. Or if you update a document with a whole page of multiple paragraphs, that could also be one commit. You'll get the idea.

Once you have made changes make sure that you commit them (save them) to the local Git server on your development platform. If you have configured GPG keys in your global setting you will not need to enter them again and they will be used to sign your commit by default. If you have not configured your GPG keys, you will need to add the ```-S``` flag to the ```git commit``` command. See the link here on [how to sign commits](https://docs.github.com/en/authentication/managing-commit-signature-verification/signing-commits).

If you are a Juniper employee, [make sure that you sign your commit](https://docs.github.com/en/authentication/managing-commit-signature-verification/signing-commits) with the key that is tied to your corporate email address.

Repeat the [Add](#add-your-work) and [Commit](#commit-locally) steps until you are done, and have enough content that you want to push back up to your GitHub.com account.

### Push to Origin

The act of pushing will transfer the work that you have committed on your local development Git server to the central servers at GitHub.com. The name ```origin``` is a reserved name that simply means the remote parent where the repository was cloned from. If you are working with Git on a remote development system, ```origin``` will typically be the parent repository under your GitHub.com account. 

### Create a Pull Request on the Upstream

When you are finally ready to contribute your work back into the upstream source, you will need to create a Pull Request from the repository branch on your GitHub.com account, which will notify the owners of the upstream repository of your changes. For more details about pull requests please read [this link ](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-pull-requests) and then follow the [steps here](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request) to create the request.

### Thank you!

The administrators of the upstream repository will review your pull request and if your additions or changes meet their standard they will merge your work from your branch in with the original upstream repository. Note that unsigned commits and pushes will take longer to review and may be rejected. Well done, and thank you for your contribution!