# Veracode Workspace Auto Create

Uses the Veracode Agent Based Scan API and other Veracode REST APIs to automatically create a workspace for application profiles in a Veracode organization.

This script assumes that (a) you already use Veracode Static Analysis and (b) you want a separate workspace for each application profile.

The script can also be used to clean up workspaces that have no projects.

## Setup

Clone this repository:

    git clone https://github.com/tjarrettveracode/veracode-workspace-auto-create

Install dependencies:

    cd veracode-workspace-auto-create
    pip install -r requirements.txt

(Optional) Save Veracode API credentials in `~/.veracode/credentials`

    [default]
    veracode_api_key_id = <YOUR_API_KEY_ID>
    veracode_api_key_secret = <YOUR_API_KEY_SECRET>

## Run

If you have saved credentials as above you can run:

    python vcworkspace.py (arguments)

Otherwise you will need to set environment variables before running `vcworkspace.py`:

    export VERACODE_API_KEY_ID=<YOUR_API_KEY_ID>
    export VERACODE_API_KEY_SECRET=<YOUR_API_KEY_SECRET>
    python vcworkspace.py (arguments)

## Arguments

    1. -a --app_id  # Application GUID for which you want to create a worksapce
    2. -l, --all   # If "true", will be applied for all applications in the organization.
    3. -c, --cleanup # If "true", will DELETE all workspaces without projects

## Notes

- To be able to use the SCA Agent API to create workspaces for applications, you must have a user account with the Security Lead or Creator role, as described in the [Veracode Help Center](https://help.veracode.com/go/c_role_permissions)
