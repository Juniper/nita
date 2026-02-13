# NITA Project Utility (`nitaprj.sh`)

This utility script helps you create, build, and manage NITA-based network automation projects using predefined profiles.

## Features

- **Project Creation:**  
  Create a new project directory from a profile template (default: `generic`).

- **Project Build:**  
  Package your project files into a zip archive and generate an Excel summary of variables, with sensitive environment variables scrubbed.

- **Version Display:**  
  Show the script version.

## Usage

You can run the script in two ways, depending on your current directory:

### 1. From Outside the Project Directory

Call the script as `nitaprj.sh` and specify the project name as an argument:

```sh
./nitaprj.sh build <projectname>
```

### 2. From Inside the Project Directory

Call the script as `nitaprj` (the script creates a symlink with this name in each project). The script automatically detects it is running inside a project by the name it is called:

```sh
./nitaprj build
```

### Commands

- `create <projectname> [profilename]`  
  Create a new project directory using the specified profile (default: `generic`).  
  **Note:** The `create` command can only be run from outside the project directory.

- `build <projectname>`  
  Build the specified project (creates a zip archive and an xlsx file).

- `version`  
  Display the script version.

### Example

```sh
# Create a new project called myproject (from outside any project directory)
./nitaprj.sh create myproject

# Build the project from outside the project directory
./nitaprj.sh build myproject

# Or, build the project from inside the project directory
cd myproject
./nitaprj build
```

## Notes

- The script will prompt to install `yaml2xls.py` if not found, which is required for generating the Excel file.
- Sensitive environment variables in `group_vars/env.yaml` are scrubbed before packaging.
- The script expects a `manifest` file in the project directory to determine which files to include in the archive.
- The script distinguishes between being run from inside or outside a project directory by checking the name it is called with (`nitaprj.sh` vs `nitaprj`).

## Directory Structure

- `profiles/` - Contains project templates (profiles).
- `group_vars/` and `host_vars/` - Ansible variable files.
- `manifest` - List of files/directories to include in the build archive.

## License

See individual files for license information.  
Default profile and scripts are licensed under the Apache 2.0 License.

---