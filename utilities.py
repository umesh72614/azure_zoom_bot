import os
from datetime import datetime
import requests
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
