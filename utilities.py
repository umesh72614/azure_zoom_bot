import os
from datetime import datetime
import requests
from constants import USERS_PATH, NAME, BAR
import json
from zipfile import ZipFile
import urllib3
urllib3.disable_warnings()


# get formatted date
# done | checked > testing pending
def get_formatted_date(datetime_obj=datetime.now(), date_format="%Y-%m-%d"):
    return datetime_obj.strftime(date_format)


# get formatted date
# done | checked > testing pending
def get_formatted_time(datetime_obj=datetime.now(), time_format="%H-%M-%S"):
    return datetime_obj.strftime(time_format)


# get formatted date and time
# done | checked > testing pending
def get_formatted_date_time(datetime_obj=datetime.now(), date_format="%Y-%m-%d", time_format="%H-%M-%S", sep='_'):
    date, time = datetime_obj.strftime(date_format), datetime_obj.strftime(time_format)
    return date + sep + time


# validate the given path
# done | checked > testing pending
def validate_path(path, make_path_dir=False):
    """Validate given directory path OR filepath. If make_path_dir=True then make path if not exist"""
    # os.path.exits() is smart enough to know if path is dir or not
    # i.e it treats './dir' and './dir/' as same but for it, './file' and './file/' are two different files
    if not os.path.exists(path):
        if make_path_dir:
            # os.makedirs rstrips '/' from dir_path
            os.makedirs(path, exist_ok=True)
            return True
        else:
            return False
    return True


# generate path
# done | checked > testing pending
def gen_path(root=os.getcwd(), pathname='', make_path_dir=False, make_root_dir=False):
    path = root.rstrip('/') + '/' + pathname.lstrip('./')
    if not validate_path(path, make_path_dir=make_path_dir):
        validate_path(root, make_path_dir=make_root_dir)
    return path


# download file from url
# done | checked > testing pending
def download_file(url, root=f'{os.getcwd()}/', filename=None, chunk_size=1024, save=True, want_data=False, force=True):
    """Download File in RAM (want_data) or Disk (save in given directory) for given Direct File Download url"""
    if filename is None:
        filename = url.split('/')[-1]
    filepath = gen_path(root, filename, make_root_dir=True)
    if validate_path(filepath) and not force:
        print(f"{filename} File is already Downloaded in {filepath}")
    else:
        # stream=True for receiving data in chunks (helps in saving RAM) that's why opening request in with
        with requests.get(url, stream=True, verify=False) as response:
            with open(filepath, 'wb') as file:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    # filter out keep-alive new chunks
                    if chunk:
                        if save:
                            file.write(chunk)
    if want_data:
        with open(filepath, 'rb') as file:
            data = file.read()
    if not save:
        os.remove(path=filepath)
    if want_data and save:
        return filename, data
    elif want_data:
        return None, data
    elif save:
        return filename, None
    else:
        return None, None


# get meeting dict info
# done | checked > testing pending
def get_meeting_dict_info(key, meeting_dict=None, users_dict=None, user_id=None, meeting_index=None, default=None):
    if meeting_dict:
        return meeting_dict.get(key, default)
    users_dict = json.load(open(USERS_PATH, 'r')) if not users_dict else users_dict
    if users_dict and user_id and meeting_index:
        return users_dict.get(user_id, {})['zoom']['meetings'][meeting_index].get(key, default)


# update meeting dict info
# done | checked > testing pending
def update_meeting_dict_info(user_id, meeting_index, meeting_update_dict, users_dict=None):
    users_dict = json.load(open(USERS_PATH, 'r')) if not users_dict else users_dict
    try:
        users_dict.get(user_id, {}).get('zoom', {}).get('meetings', [{}])[meeting_index].update(meeting_update_dict)
    except IndexError:
        return False
    else:
        json.dump(users_dict, open(USERS_PATH, 'w'), indent=4)
        return True


# Get Header
# done | checked > testing pending
def get_header():
    header = '\t' + BAR + f'\n* Zoom Bot Developed with ❤️ by: {NAME} *\n'
    header += '\t' + BAR + f'\n* Zoom Bot Logging at [{get_formatted_date_time()}] *\n'
    header += '\t' + BAR + '\n\n'
    return header


# Get Footer
# done | checked > testing pending
def get_footer():
    footer = f'\n* Copyright © 2021 Zoom Bot | {NAME} | All Rights Reserved *\n\n'
    return footer


# Save info into file
# done | checked > testing pending
def save_info(info, filepath, mode='a+', info_name='info', add_header=True, add_footer=True):
    # info = get_header() if add_header else '' + info
    # below is correct while above is incorrect
    info = get_header() + info if add_header else '' + info
    # info = info + '\n' + get_footer() if add_footer else ''
    # below is correct while above is incorrect
    info = info + '\n' + get_footer() if add_footer else info + '\n' + ''
    try:
        with open(filepath, mode) as file:
            file.write(info)
    except Exception as err_msg:
        print(f"Couldn't save {info_name}! Error occurred!")
        print(err_msg)
        return False
    else:
        print(f"{info_name} is saved Successfully!")
        return True


# Save zip file
# done | checked > testing pending
# [MUST READ] reference: https://stackoverflow.com/questions/27991745/zip-file-and-avoid-directory-structure
def save_zip(zip_filepath, files: list, mode='w', filename='zip_file'):
    try:
        with ZipFile(zip_filepath, mode) as zip_file:
            for file in files:
                # second parameter is used to avoid building whole directory structure inside zip
                zip_file.write(file, file.split('/')[-1].strip())
    except Exception as err_msg:
        print(f"Couldn't save {filename}! Error occurred!")
        print(err_msg)
        return False
    else:
        print(f"{filename} is saved Successfully!")
        return True

