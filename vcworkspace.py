import sys
import argparse
import logging
import json
import time
import string
import datetime

import anticrlf
from veracode_api_py import VeracodeAPI as vapi

log = logging.getLogger(__name__)

def setup_logger():
    handler = logging.FileHandler('vcworkspace.log', encoding='utf8')
    handler.setFormatter(anticrlf.LogFormatter('%(asctime)s - %(levelname)s - %(funcName)s - %(message)s'))
    logging.basicConfig(level=logging.INFO, handlers=[handler])

def creds_expire_days_warning():
    creds = vapi().get_creds()
    exp = datetime.datetime.strptime(creds['expiration_ts'], "%Y-%m-%dT%H:%M:%S.%f%z")
    delta = exp - datetime.datetime.now().astimezone() #we get a datetime with timezone...
    if (delta.days < 7):
        print('These API credentials expire ', creds['expiration_ts'])

def get_app_info(guid):
    log.debug('Getting application info for guid {}'.format(guid))
    app_info = vapi().get_app(guid)
    return app_info

def create_workspace(app_info):
    app_id = app_info['guid']
    app_name = app_info['profile']['name']
    app_teams = app_info['profile']['teams']

    workspace_name = get_workspace_name(app_name)
    log.info('Application name "{}" will have workspace name "{}" due to workspace naming requirements'.format(app_name,workspace_name))

    #check to see if workspace already exists
    existing_workspace = vapi().get_workspace_by_name(workspace_name)

    if ((existing_workspace != []) and (existing_workspace[0].get('id','') != '')):
        warning = "There is already a workspace named {} for application guid {}".\
            format(workspace_name, app_id)
        log.warning(warning)
        print(warning)
        return 0

    #create the workspace with the SCA API
    workspace_guid = vapi().create_workspace(workspace_name)

    #assign the teams with the SCA API
    if app_teams != []:
        for team in app_teams:
            team_id = team['team_id']
            vapi().add_workspace_team(workspace_guid,team_id)

    success = "Created workspace named {} with {} teams".format(workspace_name, len(app_teams))
    log.info(success)
    #print(success)

def get_workspace_name(app_name):
    if not (app_name[:1].isalpha()):
        workspacename = "A" + app_name #force initial alpha character
    else:
        workspacename = app_name

    #handle special characters
    valid_characters = string.ascii_letters + string.digits + ' -_'

    workspacename = "".join([ch for ch in workspacename if ch in valid_characters])

    workspacename = workspacename[0:20] # only the first 20 characters
    return workspacename

def delete_workspaces():
    workspaces = get_workspaces()
    print("Evaluating {} workspaces for deletion".format(len(workspaces)))

    deleted = 0
    for workspace in workspaces:
        deleted += delete_workspace(workspace)
    success = "Deleted {} workspaces".format(deleted)
    log.info(success)
    print(success)

def get_workspaces():
    return vapi().get_workspaces()

def get_project_count(workspace):
    return workspace.get('projects_count',0)

def delete_workspace(workspace):
    projects = get_project_count(workspace)
    if projects == 0:
        log.info("Deleting workspace {} (ID {})".format(workspace['name'],workspace['id']))
        vapi().delete_workspace(workspace['id'])
        return 1
    else:
        log.info("Skipping workspace {} (ID {}) with {} projects".format(workspace['name'],\
            workspace['id'],projects))
        return 0

def main():
    parser = argparse.ArgumentParser(
        description='This script sets up a new workspace in Veracode SCA for the application profile(s) \
            specified in the arguments, and assigns teams based on the application profile settings.')
    parser.add_argument('-a', '--app_id', help='App GUID for which to set up a workspace. Ignored if -l is provided.')
    parser.add_argument('--all', action="store_true", help='If specified, set up workspaces for all applications.')
    parser.add_argument('--cleanup', action="store_true", help='If specified, delete all workspaces with no projects.')
    args = parser.parse_args()

    # CHECK FOR CREDENTIALS EXPIRATION
    creds_expire_days_warning()

    # set up args

    app_id = args.app_id
    app_all = args.all
    cleanup = args.cleanup

    if app_all:
        apps = vapi().get_apps()
        print("Evaluating {} applications for workspace creation".format(len(apps)))

        for app_info in apps:
            create_workspace(app_info)
    elif cleanup:
        delete_workspaces()
    else:
        if app_id == None:
            print('You must provide an app_id or set --all or --cleanup to "TRUE".')
            return 0
        
        app_info = get_app_info(app_id)
        create_workspace(app_info)

if __name__ == '__main__':
    setup_logger()
    main()
