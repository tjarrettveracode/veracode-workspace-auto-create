import requests
import sys
import argparse
import logging
import json
import time
import string
import datetime

from veracode_api_py import VeracodeAPI as vapi
#from helpers.api import VeracodeAPI as vapi

def creds_expire_days_warning():
    creds = vapi().get_creds()
    exp = datetime.datetime.strptime(creds['expiration_ts'], "%Y-%m-%dT%H:%M:%S.%f%z")
    delta = exp - datetime.datetime.now().astimezone() #we get a datetime with timezone...
    if (delta.days < 7):
        print('These API credentials expire ', creds['expiration_ts'])

def get_app_info(guid):
    logging.debug('Getting application info for guid {}'.format(guid))
    app_info = vapi().get_app(guid)
    return app_info

def create_workspace(app_info):
    app_id = app_info['guid']
    app_name = app_info['profile']['name']
    app_teams = app_info['profile']['teams']

    workspace_name = get_workspace_name(app_name)
    logging.info('Application name "{}" will have workspace name "{}" due to workspace naming requirements'.format(app_name,workspace_name))

    #check to see if workspace already exists
    existing_workspace = vapi().get_workspace_by_name(workspace_name)

    if existing_workspace != []:
        if existing_workspace[0].get('id','') != '':
            warning = "There is already a workspace named {} for application guid {}".format(workspace_name, app_id)
            logging.info(warning)
            print(warning)
            return 0

    #create the workspace with the SCA API
    payload = {'name':workspace_name}
    payloadObject = json.dumps(payload)
    logging.debug("Sending payload {}".format(payloadObject))
    workspace_location = vapi().create_workspace(payloadObject)
    logging.debug("Workspace location url is {}".format(workspace_location))

    workspace_guid = get_workspace_guid_from_location(workspace_location)
    logging.debug("Workspace guid is {}".format(workspace_guid))

    #assign the teams with the SCA API
    if app_teams != []:
        for team in app_teams:
            team_id = team['team_id']
            vapi().add_workspace_team(workspace_guid,team_id)

    success = "Created workspace named {} with {} teams".format(workspace_name, len(app_teams))
    logging.info(success)
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

def get_workspace_guid_from_location(loc):
    return loc.split("/")[-1]

def delete_workspaces():
    workspaces = get_workspaces()
    print("Evaluating {} workspaces for deletion".format(len(workspaces)))

    deleted = 0
    for workspace in workspaces:
        deleted += delete_workspace(workspace)
    success = "Deleted {} workspaces".format(deleted)
    logging.info(success)
    print(success)

def get_workspaces():
    return vapi().get_workspaces()

def get_project_count(workspace):
    return workspace.get('projects_count',0)

def delete_workspace(workspace):
    projects = get_project_count(workspace)
    if projects == 0:
        logging.info("Deleting workspace {} (ID {})".format(workspace['name'],workspace['id']))
        vapi().delete_workspace(workspace['id'])
        return 1
    else:
        logging.info("Skipping workspace {} (ID {}) with {} projects".format(workspace['name'],\
            workspace['id'],projects))
        return 0

def main():
    parser = argparse.ArgumentParser(
        description='This script sets up a new workspace in Veracode SCA for the application profile(s) \
            specified in the arguments, and assigns teams based on the application profile settings.')
    parser.add_argument('-a', '--app_id', help='App GUID for which to set up a workspace. Ignored if -l is provided.')
    parser.add_argument('-l', '--all', help='If set to "TRUE", set up workspaces for all applications.')
    parser.add_argument('-c', '--cleanup', help='If set to "TRUE", delete all workspaces with no projects.')
    args = parser.parse_args()

    logging.basicConfig(filename='vcworkspace.log',
                        format='%(asctime)s - %(levelname)s - %(funcName)s - %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S%p',
                        level=logging.INFO)

    # CHECK FOR CREDENTIALS EXPIRATION
    creds_expire_days_warning()

    # set up args

    app_id = args.app_id
    app_all = ( args.all == "TRUE")
    cleanup = (args.cleanup == "TRUE")

    if app_all:
        apps = vapi().get_apps()
        print("Evaluating {} applications for workspace creation".format(len(apps)))

        for app_info in apps:
            r = create_workspace(app_info)
    elif cleanup:
        delete_workspaces()
    else:
        if app_id == None:
            print('You must provide an app_id or set --all or --cleanup to "TRUE".')
            return 0
        
        app_info = get_app_info(app_id)
        r = create_workspace(app_info)

if __name__ == '__main__':
    main()

""" 


#Workspaces must have teams/members assigned to them based on teams/users assigned to the application
#1:1 relationship for applications:workspaces 
#1.Pull Application Profile (https://app.swaggerhub.com/apis/Veracode/veracode-applications_api_specification/1.0)
#2.Pull teams for application profile 
#3.Create Integrated SCA Workspace based on Application Profile (https://app.swaggerhub.com/apis/Veracode/veracode-sca_agent_api_specification/3.0)
#4.Assign AP teams to Workspaces


#
#declare input and output files
#
#appFile = r"applicationsFile.json"
appFile = r"appslist.json"
workspaceFile = r"workspaceFile.json"

appNameList = [] #List of application names from platform
wrksNameList = []
teamsGuid = [] #This is the list that is going to have the team and guid to pass to addWorkspaceteams
rows = 60 #This may need to be changed to fit Experian applications sizes
columns = 2 #Should only need 2 columns for app name team id, workspace name and guid 
nList = [[0 for x in range(columns)] for y in range(rows)] #list to store application and team id to search and compare
gList = [[0 for x in range(columns)] for y in range(rows)] #list to store workspace name and guid to search and compare
finalTeamList = []
sortedApp = []
sortedWrks = []
region = []

#
# API ID/Key of the platform
#
vid_platform = ""
vkey_platform = ""


#
# Parse JSON data to obtain such as application Names and teams ID
# 
def parseAppJSON(filename):
    with open(filename,"r") as json_file: 
        apps = json.loads(json_file.read())['_embedded']['applications']
        #Need to write to array - print for now
        for row in apps:
            appName = row['profile']['custom_fields'][0]['value']
            region = row['profile']['custom_fields'][1]['value']
            appName_region = (region + ' ' + appName)
            appNameList.append(region+ ' ' + appName) #Append the platform names to list used to create workspace later
            for team_id in row['profile']['teams']:
                teamID = (team_id['team_id'])
                teamName = (team_id['team_name'])
                nList.append([appName_region,teamID,teamName]) #Appends app name and team id to List
        print(nList) #Debug only

#
# Now that we have the GUID we can add teams to workspaces
#
def addWorkspaceTeams(guid, team_id):
    try:
        print (guid, team_id)
        resp = requests.put(
            'https://api.veracode.com/srcclr/v3/workspaces/' + guid + '/teams/' + team_id, 
            headers={'User-Agent': 'HTTPie/2.0.0', 'Accept': 'application/json'},
            auth=RequestsAuthPluginVeracodeHMAC(vid_platform,vkey_platform))
    except Exception as err:
        print(f'Error occurred: {err}')
        sys.exit(1)

    else:
        #print data to standard output
        print(f'Req Headers: {resp.request.headers}') #Used for debug
        print(f'Resp Code: {resp.status_code}\nResp Text: {resp.text}')
        
#
# Map Workspaces
#
def mapWorkspaces (wlist):
    #Create the workspaces from the sorted list
    for i in wlist:
        print(i)
        creaetWorkspaces(i) #Pass in appName/workspace name from the sorted list
        time.sleep(10)

#
# Map Teams
#      
def mapTeams (nlist, glist):
    for a in nlist:
        for b in gList:
            if a[0] == b[0]: #compare application name with workspace name. If match append team id and guid id
                teamsGuid.append((a[1], b[1]))
                break
    #
    # need to remove empty or 0 fields from the list
    #
    for item in teamsGuid:
        if item!=(0,0):  
            finalTeamList.append(item)

    #
    # Now that we parsed and massaged the data we need, we can add the teams to the workspaces
    #
    for a in finalTeamList:
        #print statements used to see what the data looks like before adding teams
        print(a[0], a[1]) #for Testing
        addWorkspaceTeams(str(a[1]), str(a[0]))
        time.sleep(1)

#
# Call getPlatformApps() to generate JSON file with applications names and team id
#
getPlatformApps() 
#
# Create nList names and team ID's to feed to createWorkspace
#
parseAppJSON(appFile)
#
# Need to get the workspace guid to add the teams
#
getWorkspaces()
#
#parse the JSON data and create gList
#
parseGUIDJSON(workspaceFile) 
#
#Sort all lists in use
#
sortedApp = sorted(appNameList)     
sortedWrks = sorted(wrksNameList)
#
#Get the difference between lists so we don't try to create workspace already with same app name
#
workSpaceList = list(set(sortedApp).difference(sortedWrks)) 
workSpaceListSorted = sorted(workSpaceList)
#
#Create the workspaces from the sorted list 
#
mapWorkspaces(workSpaceListSorted) #calls createWorkspaces
#
#Map the teams
#
#mapTeams(nList, gList)
#Check SCA
#The ENd
 """