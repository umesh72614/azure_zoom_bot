# GMail API
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
# Emails
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email import encoders
from email.mime.multipart import MIMEMultipart
import mimetypes
import base64
import json
# Selenium Web Driver
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.chrome.options import Options
# PyAutoGUI
import pyautogui as pag
# Others
import pickle
import random
import time
import os
import sys
from datetime import datetime
from constants import *
from pprint import pprint
from shutil import make_archive
from zipfile import ZipFile
from utilities import *

# global var
INDEX = random.choice([1, 2, 3])
RECAP_IMAGE_XPATH = f'//*[@id="rc-imageselect-target"]/table/tbody/tr[{INDEX}]/td[{INDEX}]'
# SS_FORCE = False
SS_FORCE = True
IS_HEADLESS = True
# IS_HEADLESS = False

"""
NOTE: If you are joining zoom by browser and you successfully joined it but closed the window/ tab without leaving
the meeting, then, you will still be shown available on the meeting for some minutes (about 1-2)!! So be careful while 
joining browser meetings of zoom, if you are not logged in or not saving cookies and you close browser in between, 
you will still be present in the meeting for few minutes!!
NOTE: Helpful crontab tool: https://crontab.guru/ and https://cronitor.io/
"""


# get meeting dict info
# done | checked > testing pending
def get_meeting_dict_info(key, meeting_dict=None, users_dict=None, user_id=None, meeting_index=None, default=None):
    if meeting_dict:
        return meeting_dict.get(key, default)
    users_dict = json.load(open('users.json', 'r')) if not users_dict else users_dict
    if users_dict and user_id and meeting_index:
        return users_dict.get(user_id, {})['zoom']['meetings'][meeting_index].get(key, default)


# update meeting dict info
# done | checked > testing pending
def update_meeting_dict_info(user_id, meeting_index, meeting_update_dict, users_dict=None):
    users_dict = json.load(open('users.json', 'r')) if not users_dict else users_dict
    try:
        users_dict.get(user_id, {}).get('zoom', {}).get('meetings', [{}])[meeting_index].update(meeting_update_dict)
    except IndexError:
        return False
    else:
        json.dump(users_dict, open('users.json', 'w'), indent=4)
        return True


# Send Email with GMail API
class SendEmail:
    # init
    def __init__(self, sender, to, subject, message_text, files: list,
                 cc, bcc='', json_path=JSON_PATH, token_path=TOKEN_PATH):
        self.sender = sender
        self.to = to
        self.subject = subject
        self.message_text = message_text
        self.files = files
        self.file = None
        self.cc = cc
        self.bcc = bcc
        self.json_path = json_path
        self.token_path = token_path
        self.scopes = SCOPES
        self.service = None
        self.message = None

    def send_email_with_gmail_api(self):
        """Send email with Gmail API (wrapper function)"""
        # build service
        self.service = self.build_service()
        # generate email message
        self.message = self.create_message_with_attachment()
        # send email if message
        if self.message:
            print("Message is generated successfully!")
            res = self.send_message()
            if res:
                print("Email sent successfully!")

    def build_service(self):
        credentials = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first time.
        if os.path.exists(self.token_path):
            credentials = Credentials.from_authorized_user_file(self.token_path, SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.json_path, SCOPES)
                credentials = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(self.token_path, 'w') as token:
                token.write(credentials.to_json())
        # build the service
        service = build('gmail', 'v1', credentials=credentials)
        return service

    def create_message_with_attachment(self):
        """Create a message for an email.
        Returns:
        An object containing a base64url encoded email object.
        """
        message = MIMEMultipart()
        message['to'] = self.to
        message['from'] = self.sender
        message['cc'] = self.cc
        message['bcc'] = self.bcc
        message['subject'] = self.subject

        msg = MIMEText(self.message_text)
        message.attach(msg)

        # Attach a list of files
        for file in self.files:
            self.file = file
            content_type, encoding = mimetypes.guess_type(self.file)
            if content_type is None or encoding is not None:
                content_type = 'application/octet-stream'
            main_type, sub_type = content_type.split('/', 1)
            with open(self.file, 'rb') as fp:
                if main_type == 'text':
                    msg = MIMEText(fp.read(), _subtype=sub_type)
                elif main_type == 'image':
                    msg = MIMEImage(fp.read(), _subtype=sub_type)
                elif main_type == 'audio':
                    msg = MIMEAudio(fp.read(), _subtype=sub_type)
                else:
                    msg = MIMEBase(main_type, sub_type)
                    msg.set_payload(fp.read())
            # encode the file -> credit: https://www.geeksforgeeks.org/send-mail-attachment-gmail-account-using-python/
            encoders.encode_base64(msg)
            # set name of the file from its path
            filename = os.path.basename(self.file)
            # add info to header about the file attachment
            msg.add_header('Content-Disposition', 'attachment', filename=filename)
            # finally attach it to message
            message.attach(msg)
        # credit for below: https://stackoverflow.com/a/46668827
        b64_bytes = base64.urlsafe_b64encode(message.as_bytes())
        b64_string = b64_bytes.decode()
        return {'raw': b64_string}

    def send_message(self, user_id="me"):
        """Send an email message."""
        # me -> authenticated user => sender
        try:
            # pylint: disable=maybe-no-member
            message = (self.service.users().messages().send(userId=user_id, body=self.message).execute())
            print('Message Id:', message['id'])
            return message
        except Exception as error:
            print('An error occurred:', error)


# json.dump(users, open('users.json', 'w'), indent=4)
# users_dict = json.load(open('users.json', 'r'))
# pprint(users_dict)


# Chrome Driver
class ChromeDriver:
    # init
    def __init__(self, is_headless, **kwargs):
        # want headless -> if true then only print else won't print
        self.is_headless = is_headless
        # screenshot
        self.profile_root = kwargs.get('profile_root', f'{os.getcwd()}/chrome')
        self.profile_root.rstrip('/')
        os.makedirs(self.profile_root, exist_ok=True)
        self.ss_dir = kwargs.get('ss_dir', self.profile_root + '/screenshots')
        os.makedirs(self.ss_dir, exist_ok=True)
        self.cookies_dir = kwargs.get('cookies_dir', self.profile_root + '/cookies')
        os.makedirs(self.cookies_dir, exist_ok=True)
        self.download_dir = kwargs.get('download_dir', self.profile_root + '/downloads')
        os.makedirs(self.download_dir, exist_ok=True)
        self.profile_dir = kwargs.get('profile_dir', self.profile_root + '/chrome_profile')
        os.makedirs(self.profile_dir, exist_ok=True)
        self.include_fake_media = kwargs.get('include_fake_media', False)
        self.include_notify = kwargs.get('include_notify', True)
        self.block_popups = kwargs.get('block_popups', True)
        self.is_mute = kwargs.get('is_mute', True)
        self.clean_chrome = kwargs.get('cleanup_chrome', False)
        # chromedriver options
        chrome_options, desired_cap = self.chromedriver_options_cap()
        # driver object for handling chrome with se using chrome driver
        self.driver = webdriver.Chrome(executable_path=CHROME_DRIVER_PATH, options=chrome_options,
                                       desired_capabilities=desired_cap)

    # set chromedriver desired capabilities and options
    def chromedriver_options_cap(self):
        # chromedriver options
        chrome_options_list = CHROME_OPTIONS[:]
        chrome_options_list += [f'--user-data-dir={self.profile_dir}'] if self.profile_dir else []
        chrome_options_list += HEADLESS_OPTIONS if self.is_headless else []
        chrome_options_list += FAKE_STREAM_OPTIONS if self.include_fake_media else []
        chrome_options_list += ['--mute-audio'] if self.is_mute else []
        chrome_options = Options()
        for option in chrome_options_list:
            chrome_options.add_argument(option)
        # chromedriver preferences
        prefs = {"download.default_directory": f'{self.download_dir}',
                 "savefile.default_directory": f'{self.download_dir}'}
        prefs.update(NOTIFY_PREF if self.include_notify else {})
        chrome_options.add_experimental_option('prefs', prefs)
        chrome_options_dict = {'args': chrome_options_list, 'prefs': prefs}
        # reference: https://www.browserstack.com/docs/automate/selenium/enable-pop-ups#python
        chrome_options_dict.update({"excludeSwitches": ["--disable-popup-blocking"]} if self.block_popups else {})
        # reference: https://www.browserstack.com/docs/automate/selenium/enable-pop-ups#python
        chrome_options.add_experimental_option('excludeSwitches', ["--disable-popup-blocking"])
        # chromedriver desired capabilities
        desired_cap = DesiredCapabilities.CHROME.copy()
        # desired_cap.update({'chromeOptions': chrome_options_dict})
        return chrome_options, desired_cap

    # create a safer function for wait
    def custom_wait(self, timeout=1.0):
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".NULL_PTR"))).click()
        except Exception:
            return

    # create a safer function for clicking element using WebDriverWait
    def action_with_web_driver_wait(self, locator, selector, index=0, action="click", keys=None,
                                    time_out=TIME_OUT, tries=TRIES):
        """NOTE: WebDriverWait func has a flaw as it can only click the first element with given locator and selector"""
        # wait till tries
        i = 0
        while True and i <= tries:
            try:
                if index == 0:
                    if action == "click":
                        # Initialize and wait till element(link) became clickable - timeout in TIMEOUT seconds
                        WebDriverWait(self.driver, time_out).until(
                            EC.element_to_be_clickable((locator, selector))).click()
                    else:
                        WebDriverWait(self.driver, time_out).until(
                            EC.presence_of_element_located((locator, selector))).send_keys(keys)
                else:
                    if action == "click":
                        # element at index
                        self.driver.find_elements(locator, selector)[index].click()
                    else:
                        self.driver.find_elements(locator, selector)[index].send_keys(keys)
            except Exception:
                if index == 0:
                    # Try Locating the element(s)
                    WebDriverWait(self.driver, time_out).until(EC.presence_of_element_located((locator, selector)))
                else:
                    WebDriverWait(self.driver, time_out).until(EC.presence_of_all_elements_located(
                        (locator, selector)))
                i += 1
            else:
                break

    # capture ss with driver
    def capture_ss(self, element=None, ss_root='', ss_name='screenshot.png', force=False, append_time=True):
        if not ss_root:
            ss_root = self.ss_dir
        if append_time:
            ss_name = ss_name.split('.png')[0].strip() + '_' + get_formatted_date_time() + '.png'
        if self.is_headless or force:
            ss_path = gen_path(ss_root, ss_name)
            if element:
                element.screenshot(ss_path)
            else:
                self.driver.save_screenshot(ss_path)

    # get element attribute with driver
    def get_ele_attr(self, element, attr_name='innerText', use_js=False):
        try:
            attr = element.get_attribute(attr_name) if not use_js else self.driver.execute_script(
                f"return arguments[0].{attr_name};", element)
        except Exception:
            return None
        else:
            return attr

    # get element attribute (wrapper) with driver
    # verbose: 0 -> nothing is printed
    # verbose: 1 -> found is printed
    # verbose: 2 -> not found is printed
    # verbose: >=3 -> everything is printed
    def get_element_attribute(self, element, ele_name='Element', attr_name='innerText', is_attr_str=True, try_alt=False,
                              use_js=False, verbose=0):
        attr = self.get_ele_attr(element, attr_name, use_js)
        if attr_name == 'innerText' and not attr and try_alt:
            attr = self.get_ele_attr(element, 'innerHTML', use_js)
        if attr_name == 'innerText' and not attr and try_alt:
            attr = self.get_ele_attr(element, 'innerText', use_js)
        if is_attr_str and attr is not None:
            attr = str(attr).strip()
        if attr is None and (verbose == 2 or verbose >= 3):
            print(f"{attr_name} for {ele_name} is not found!")
        elif attr is not None and (verbose == 1 or verbose >= 3):
            print(f"{attr_name} for {ele_name} is found: {attr}")
        return attr

    # get element and its attribute with driver
    # verbose: 0 -> nothing is printed
    # verbose: 1 -> element/attr found is printed
    # verbose: 2 -> element/attr not found is printed
    # verbose: >=3 -> everything is printed
    def get_element_and_attribute(self, locator, selector, ele_name='Element', attr_name='innerText', try_alt=False,
                                  is_attr_str=True, use_js=False, ele_verbose=0, attr_verbose=0):
        try:
            element = WebDriverWait(self.driver, TIME_OUT).until(
                EC.presence_of_element_located((locator, selector)))
        except Exception:
            if ele_verbose == 2 or ele_verbose >= 3:
                print(f"{ele_name} is not found!")
            return None, None
        else:
            if ele_verbose == 1 or ele_verbose >= 3:
                print(f'{ele_name} is found!')
            attr = self.get_element_attribute(element, ele_name, attr_name, is_attr_str, try_alt, use_js, attr_verbose) \
                if attr_name else None
            return element, attr

    # open url with driver
    def open_url(self, url):
        self.driver.get(url)

    # add cookies with driver: Cookies Domain must match with current url domain. Alt: better use custom chrome profile
    def add_cookies(self):
        cookies_path = gen_path(self.cookies_dir, 'cookies.pkl')
        cookies = pickle.load(open(cookies_path, 'rb'))
        for cookie in cookies:
            self.driver.add_cookie(cookie)

    # save cookies with driver:
    def save_cookie(self):
        cookies_path = gen_path(self.cookies_dir, 'cookies.pkl')
        pickle.dump(self.driver.get_cookies(), open(cookies_path, "wb"))

    # quit driver
    def quit_driver(self):
        self.driver.quit()
        if self.clean_chrome:
            os.system(f'rm -rf {self.profile_root}')


# Browser for building base chrome profile
class Browser(ChromeDriver):
    # Init
    def __init__(self, is_headless, **kwargs):
        super().__init__(is_headless, **kwargs)
        self.urls, self.num_urls, self.avg_url_time, self.avg_browse_time = [], 0, 0, 0

    def build_urls(self, num_urls=0):
        self.urls, self.num_urls = URLS.copy(), len(URLS)
        random.seed(round(time.time()))
        num_urls = round(random.uniform(MIN_URLS, MAX_URLS)) if not num_urls else num_urls
        self.num_urls = num_urls
        self.avg_url_time = int((MAX_URL_TIME + MIN_URL_TIME) / 2)
        self.avg_browse_time = int((self.num_urls * self.avg_url_time) / 60)
        print("num_urls:", self.num_urls)
        print(f"min_url_time: {MIN_URL_TIME}s, max_url_time: {MAX_URL_TIME}s, avg_url_time: {self.avg_url_time}s")
        print(f"avg_browse_time: {self.avg_browse_time}min")
        # alternate: https://stackoverflow.com/a/15511372 (new_list = random.sample(list, k))
        random.shuffle(self.urls)
        self.urls = self.urls[:self.num_urls]
        return self.urls

    def browse_urls(self):
        for i, url in enumerate(self.urls):
            print(f"Browsing url[{i + 1}]: {url}")
            try:
                self.open_url(url)
                if i == 0 and not self.is_headless:
                    self.driver.minimize_window()
            except Exception as err_msg:
                print('Err in browse_urls:', err_msg)
                continue
            else:
                random.seed(round(time.time()))
                self.custom_wait(round(random.uniform(MIN_URL_TIME, MAX_URL_TIME)))
        return True

    def browse(self, num_urls=0):
        self.build_urls(num_urls)
        try:
            brw = self.browse_urls()
            if brw:
                self.save_cookie()
        except Exception as err_msg:
            print('Err in browse:', err_msg)
            self.quit_driver()
        else:
            self.custom_wait()
            self.quit_driver()


# Convert audio to text
class AudioToText(ChromeDriver):
    # init
    def __init__(self, is_headless, **kwargs):
        super().__init__(is_headless, **kwargs)
        # converted text
        self.text = ''

    def audio_to_text(self, audio_link):
        t1 = time.time()
        self.open_url(IBM_URL)
        self.action_with_web_driver_wait(By.XPATH, IBM_INPUT_XPATH, action='keys', keys=audio_link)
        self.custom_wait()
        self.action_with_web_driver_wait(By.TAG_NAME, "button", index=1)
        self.custom_wait()
        self.action_with_web_driver_wait(By.XPATH, IBM_INPUT_XPATH, action='keys', keys=audio_link)
        i, tries = 0, 4
        # t1 = time.time()
        while not self.text and i < tries:
            self.custom_wait(5)
            _, self.text = self.get_element_and_attribute(By.CLASS_NAME, IBM_TEXT_CLASS, 'text element', ele_verbose=2,
                                                          attr_verbose=2)
            i += 1
        print('time:', str(round(time.time() - t1, 3)) + 's', 'tries:', i, 'text:', self.text.strip())
        return self.text.strip()


# ReCaptcha V2 Cracker
class ReCaptchaV2Cracker:
    # init
    def __init__(self, bot):
        # Bot to be used for cracking recaptcha
        self.bot = bot
        # XPATH to recaptcha
        self.xpath = ''

        # crack mp3 file of recaptcha

    # crack mp3 file for recaptcha
    def crack_mp3(self):
        try:
            print("Working on mp3 file!")
            # dummy click on play button to make this attempt more authentic
            self.bot.custom_wait()
            self.bot.action_with_web_driver_wait(By.CLASS_NAME, RECAP_AUDIO_PLAY_BTN_CLASS)
            self.bot.custom_wait(2)
            _, link = self.bot.get_element_and_attribute(By.CLASS_NAME, RECAP_AUDIO_DOWN_CLASS, 'Link Element', 'href',
                                                         ele_verbose=2, attr_verbose=2)
            print(f'link: {link}')
            download_file(link, filename=RECAP_AUDIO_FILENAME, root=self.bot.download_dir)
            self.bot.custom_wait()
            text, i, tries = '', 0, 2
            while not text and i < tries:
                print("Calling speech to text API")
                audio = AudioToText(True, cleanup_chrome=True)
                text = audio.audio_to_text(gen_path(self.bot.download_dir, RECAP_AUDIO_FILENAME))
                audio.quit_driver()
                i += 1
            self.bot.capture_ss(ss_name='recaptcha_audio.png', force=SS_FORCE)
            self.bot.action_with_web_driver_wait(By.ID, RECAP_INPUT_ID, action='keys', keys=text)
            self.bot.custom_wait(2)
            self.bot.action_with_web_driver_wait(By.ID, RECAP_VERIFY_ID)
            # below wait is must so that innerHTML content gets changed
            # NOTE: Sometimes innerText works but sometime innerHTML, so better try both during dev/ test phase
            # In below case innerHTML worked. But a wait is required so that state of element gets changed and then
            # get fetched by selenium
            self.bot.custom_wait(2)
            # Bot got detected by Google
            error, error_label = self.bot.get_element_and_attribute(By.CLASS_NAME, RECAP_TRY_AGAIN_LATER_CLASS,
                                                                    'Err Element', attr_verbose=2)
            if error_label is not None:
                if error_label.lower() == RECAP_TRY_AGAIN_LATER_MSG.lower():
                    self.bot.capture_ss(ss_name='bot_defeated.png.png', force=SS_FORCE)
                    self.bot.failed_message = "Bot got Detected by Google! Sorry Bot is Defeated!"
                    print(self.bot.failed_message)
                    self.bot.driver.switch_to.default_content()
                    return False
                return self.crack_mp3()
            # Verify Audio again
            error, error_label = self.bot.get_element_and_attribute(By.CLASS_NAME, RECAP_AUDIO_VERIFY_AGAIN_CLASS,
                                                                    'Err Element', attr_verbose=2)
            if error_label is not None:
                if error_label.lower() == RECAP_AUDIO_VERIFY_AGAIN_MSG.lower():
                    print("MP3 Audio has to be reloaded")
                    self.bot.capture_ss(ss_name='recaptcha_audio.png', force=SS_FORCE)
                    self.bot.action_with_web_driver_wait(By.CLASS_NAME, RECAP_RELOAD_CAPTCHA_CHAL_CLASS)
                    return self.crack_mp3()
            self.bot.driver.switch_to.default_content()
            self.bot.capture_ss(ss_name='recaptcha_solved.png', force=SS_FORCE)
            print("MP3 Audio Cracked Successfully!")
            return True
        except Exception as err_msg:
            print(err_msg)
            self.bot.driver.switch_to.default_content()
            return False

    # crack audio recaptcha
    def crack_audio(self, xpath):
        # To crack audio, first randomly click on some images
        try:
            print("Clicking on some random pictures!")
            self.bot.custom_wait(2)
            WebDriverWait(self.bot.driver, TIME_OUT).until(
                EC.frame_to_be_available_and_switch_to_it((By.XPATH, xpath)))
            self.bot.custom_wait(2)
            for i in range(random.choice([1, 2, 3])):
                self.bot.custom_wait()
                if i == 0:
                    self.bot.capture_ss(ss_name='recaptcha_image.png', force=SS_FORCE)
                self.bot.action_with_web_driver_wait(By.XPATH, RECAP_IMAGE_XPATH)
                self.bot.custom_wait()
                self.bot.action_with_web_driver_wait(By.ID, RECAP_VERIFY_ID)
            self.bot.custom_wait(2)
            print("Trying on Audio Captcha!")
            self.bot.action_with_web_driver_wait(By.CLASS_NAME, RECAP_AUDIO_BTN_CLASS)
            # below wait is must
            self.bot.custom_wait(2)
            # Verify Audio again
            error, error_label = self.bot.get_element_and_attribute(By.CLASS_NAME, RECAP_TRY_AGAIN_LATER_CLASS,
                                                                    'Err Element', attr_verbose=2)
            if error_label is not None:
                if error_label.lower() == RECAP_TRY_AGAIN_LATER_MSG.lower():
                    self.bot.capture_ss(ss_name='bot_defeated.png.png', force=SS_FORCE)
                    self.bot.failed_message = "Bot got Detected by Google! Sorry Bot is Defeated!"
                    print(self.bot.failed_message)
                    self.bot.driver.switch_to.default_content()
                    return False
                return self.crack_mp3()
            return self.crack_mp3()
        except Exception:
            # even if captcha is solved at first step, the frame of recaptcha-challenge is still available, so the frame
            # actually switched without error and thus, we need to switch to default content here also.
            # the actual error occurs at trying audio captcha !!
            self.bot.driver.switch_to.default_content()
            print("Captcha was solved at first step without any effort!")
            self.bot.capture_ss(ss_name='recaptcha_solved_first.png', force=SS_FORCE)
            return True

    # crack recaptcha with driver
    def crack_captcha(self, xpath=RECAP_CHAL_IFRAME_XPATH):
        try:
            print("Solving recaptcha-v2!")
            WebDriverWait(self.bot.driver, TIME_OUT).until(
                EC.frame_to_be_available_and_switch_to_it((By.XPATH, RECAP_IFRAME_XPATH)))
        except Exception:
            self.bot.capture_ss(ss_name='no_recaptcha.png', force=SS_FORCE)
            print("No Visible ReCaptcha-v2 is found!")
            return None
        else:
            self.bot.capture_ss(ss_name='recaptcha.png', force=True)
            self.bot.action_with_web_driver_wait(By.ID, RECAP_ID)
            self.bot.custom_wait(2)
            self.bot.driver.switch_to.default_content()
            return self.crack_audio(xpath)


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


"""
Errors during Testing:
1. 
Problem: Due to Desired Cap (integration of chromeOptions dict in it didn't worked) 
Status: Solved by separating the creation of chrome_options and desired cap
2.
Problem: In func, extract_info_breakpoint, when bot fails => can't extract info like chats/participants/invite_info
Status: Partially solved by adding: if mode != 'failed' then only extract info. Need to do proper exception Handling.
3.
Problem: Paths are Blunders, func: gen_path and validate_path are creating blunders due to '/'. May be because
of this, chrome profile and base chrome profile are not getting generated successfully
Status: Solved, corrected validate_path func and gen_path func to work correctly
4.
Problem: Gmail attachment files are not getting attached to emails, Message formatting is also not correct.
Status: Corrected Paths to generate email attachments and correct save_zip function.
5. Problem: Forgot to add driver.quit inside start bot func so, drivers were running in background forever.
Status: Corrected, added the support for it inside main func.
"""


# Zoom Bot
# done | checked > testing pending
class ZoomBot(ChromeDriver):
    # init
    # done | checked > testing pending
    def __init__(self, is_headless, **kwargs):
        # Required
        self.id = kwargs['id']
        self.kwargs_path = kwargs['kwargs_path']
        self.zoom_name = kwargs['zoom_name']
        self.users_path = kwargs['users_path']
        self.zoom_meeting_index = kwargs['index']
        # Zoom Credentials
        self.zoom_email = kwargs.get('zoom_email', '')
        self.zoom_pass = kwargs.get('zoom_pass', '')
        # Zoom Meeting Registration
        self.first_name = kwargs.get('f_name', self.zoom_name.split(' ')[0].strip())
        self.last_name = kwargs.get('l_name', self.zoom_name.split(' ')[-1].strip())
        self.register_email = kwargs.get('register_email', self.zoom_email)
        # Zoom Meeting
        self.zoom_meeting_id = kwargs.get('meeting_id', '')
        self.zoom_meeting_pass = kwargs.get('meeting_pass', '')
        self.zoom_meeting_url = kwargs.get('url', '')
        self.zoom_meeting_tag = kwargs.get('tag', 'Bot Meeting' + '_' + str(self.zoom_meeting_index))
        self.email_notify = kwargs.get('email_notify', True)
        # self.zoom_meeting_start = kwargs.get('start_time', '00:00')
        self.zoom_meeting_duration = kwargs.get('duration', '00:15')
        hour, minute = self.zoom_meeting_duration.split(':')
        self.zoom_meeting_duration_min = int(hour) * 60 + int(minute)
        # GMail
        self.email = kwargs.get('email', self.zoom_email)
        self.email_notify = self.email_notify and self.email
        self.name = kwargs.get('name', "Zoom Bot's User")
        self.is_owner = kwargs.get('owner', False)
        # Zoom Bot
        self.bot_root = kwargs.get('bot_root', os.getcwd())
        # Others
        self.zoom_meeting_not_stared_tries = 0
        self.failed_message = "Sorry couldn't join Zoom meeting!"
        super().__init__(is_headless, **kwargs)

    # basic registration for meeting
    # done | checked > testing pending
    def basic_register_zoom_meeting(self, register_url, extract_info=True, extract_url=True, extract_id=True,
                                    extract_pass=True):
        try:
            print("Opening Meeting Registration Link!")
            self.open_url(register_url)
            print("Entering Basic Registration Credentials!")
            self.action_with_web_driver_wait(By.ID, ZOOM_FIRST_NAME_ID, action='keys', keys=self.first_name)
            self.action_with_web_driver_wait(By.ID, ZOOM_LAST_NAME_ID, action='keys', keys=self.last_name)
            self.action_with_web_driver_wait(By.ID, ZOOM_EMAIL_ID, action='keys', keys=self.register_email)
            self.action_with_web_driver_wait(By.ID, ZOOM_CONFIRM_EMAIL_ID, action='keys', keys=self.register_email)
            print("Entered Basic Registration Credentials Successfully!")
            self.action_with_web_driver_wait(By.ID, ZOOM_SUBMIT_BTN_ID)
        except Exception as err_msg:
            self.failed_message = "Couldn't Basic Register for Zoom Meeting! Error occurred!"
            print(self.failed_message)
            print(err_msg)
            return False
        else:
            print("Basic Registered for Zoom Meeting Successfully!")
            if extract_info:
                self.custom_wait()
                return self.extract_registration_info(extract_id, extract_pass, extract_url)
            return True

    # extract/ save registration info for meeting
    # done | checked > testing pending
    def extract_registration_info(self, extract_id=True, extract_url=True, extract_passcode=True):
        # un hide passcode if exist
        pass_available = False
        try:
            self.action_with_web_driver_wait(By.ID, ZOOM_REGISTRATION_SHOWPASS_ID)
        except Exception:
            print("Passcode isn't available on Registration Info Page!")
        else:
            pass_available = True
        self.custom_wait()
        _, registration_info = self.get_element_and_attribute(By.ID, ZOOM_REGISTRATION_INFO_ID,
                                                              'Registration Info Div', ele_verbose=2,
                                                              attr_verbose=2)
        if registration_info:
            meeting_update_dict = {}
            if extract_id:
                meeting_id = registration_info.split(ZOOM_REGISTRATION_ID_SPLITTER)[-1].strip().split('\n')[0]
                meeting_id = ''.join(meeting_id.strip().split(' ')).strip()
                if meeting_id:
                    meeting_update_dict['id'] = meeting_id
            if extract_url:
                url = registration_info.split(ZOOM_REGISTRATION_URL_SPLITTER)[-1].strip().split('\n')[0].strip()
                if url:
                    meeting_update_dict['url'] = url
            if extract_passcode and pass_available:
                passcode = registration_info.split(ZOOM_REGISTRATION_PASSCODE_SPLITTER)[-1].strip().split(' ')[
                    0].strip()
                if passcode:
                    meeting_update_dict['pass'] = passcode
            if meeting_update_dict:
                self.save_meeting_info(meeting_update_dict)
            return save_info(registration_info, gen_path(self.bot_root, 'registration_info.txt'),
                             info_name='Registration Info')
        return False

    # save/ extract meeting info to/ from dict
    # done | checked > testing pending
    def save_meeting_info(self, meeting_update_dict):
        # users = json.load(open('users.json', 'r'))
        # users[self.id]['zoom']['meetings'][self.zoom_meeting_index].update(meeting_update_dict)
        # json.dump(users, open('users.json', 'w'), indent=4)
        if update_meeting_dict_info(self.id, self.zoom_meeting_index, meeting_update_dict):
            print(f"Updated meeting info into disk Successfully!")
        self.zoom_meeting_id = meeting_update_dict.get('id', self.zoom_meeting_id)
        self.zoom_meeting_pass = meeting_update_dict.get('pass', self.zoom_meeting_pass)
        self.zoom_meeting_url = meeting_update_dict.get('url', self.zoom_meeting_url)
        print(f"Updated meeting info for Zoom Bot Successfully!")
        for key in meeting_update_dict:
            print(f"Meeting {key.upper()}:", meeting_update_dict[key])

    # done > testing pending
    def signin_zoom_credentials(self):
        try:
            print("Entering Login Credentials!")
            self.action_with_web_driver_wait(By.ID, 'email', action='keys', keys=self.zoom_email)
            self.action_with_web_driver_wait(By.ID, 'password', action='keys', keys=self.zoom_pass)
            self.action_with_web_driver_wait(By.CSS_SELECTOR, ZOOM_SIGNIN_SELECTOR)
        except Exception as err_msg:
            print("Couldn't enter Login Credentials! Error occurred!")
            self.capture_ss(ss_name='zoom_login_failed.png', force=SS_FORCE)
            print(err_msg)
            return False
        else:
            print("Entered Credentials Successfully!")
            self.capture_ss(ss_name='zoom_login.png', force=SS_FORCE)
            return True

    # done > testing pending
    def crack_zoom_login_recaptcha(self, tries=2):
        i = 0
        while self.driver.current_url in [ZOOM_SIGNIN_URL] and i < tries:
            self.capture_ss(ss_name=f'zoom_login_recaptcha_{i + 1}.png', force=SS_FORCE)
            t1 = time.time()
            captcha = ReCaptchaV2Cracker(self).crack_audio(RECAP_CHAL_LOGIN_XPATH)
            t1 = time.time() - t1
            if captcha:
                self.capture_ss(ss_name=f'zoom_login_recaptcha_defeated_{i + 1}.png', force=SS_FORCE)
                print("Zoom Login ReCaptcha is Defeated! Time taken:", str(round(t1, 3)) + 's')
                # for hidden recaptcha signin button is already pressed once recaptcha is defeated
                # self.action_with_web_driver_wait(By.CSS_SELECTOR, ZOOM_SIGNIN_SELECTOR)
            elif i < tries - 1:
                print(f"Not able to crack Zoom Login ReCaptcha [{i + 1}]! Trying Again!")
            # wait for url to reload
            self.custom_wait(5)
            i += 1
            return True
        self.custom_wait()
        if self.driver.current_url in [ZOOM_SIGNIN_URL]:
            self.capture_ss(ss_name=f'zoom_login_failed_{i}.png', force=SS_FORCE)
            print("Sorry! Zoom Login Failed!")
            return False
        else:
            self.capture_ss(ss_name=f'zoom_login_success_{i}.png', force=SS_FORCE)
            print("Zoom Logged In Successfully!")
            return True

    # done > testing pending
    def login_zoom(self):
        print("Opening Zoom Login URL!")
        self.open_url(ZOOM_SIGNIN_URL)
        self.custom_wait()
        if self.driver.current_url not in [ZOOM_PROFILE_URL]:
            enter_credentials = self.signin_zoom_credentials()
            if enter_credentials:
                self.custom_wait(5)
                self.crack_zoom_login_recaptcha()
            else:
                return False
        else:
            self.capture_ss(ss_name=f'zoom_already_login.png', force=SS_FORCE)
            print("Already Logged In!")
            return True

    # done | checked > testing pending
    def join_meeting_id(self, register=True):
        self.open_url(ZOOM_MEETING_URL)
        self.custom_wait()
        try:
            print("Entering Zoom Meeting ID!")
            self.action_with_web_driver_wait(By.ID, ZOOM_INPUT_MEETING_ID, action='keys', keys=self.zoom_meeting_id)
            self.capture_ss(ss_name='zoom_meeting_id.png', force=SS_FORCE)
            self.action_with_web_driver_wait(By.ID, ZOOM_SUBMIT_BTN_ID)
        except Exception as err_msg:
            self.failed_message = "Couldn't Enter Zoom Meeting ID! Error occurred!"
            print(self.failed_message)
            print(err_msg)
            return None
        else:
            print("Entered Zoom Meeting ID Successfully!")
            self.custom_wait()
            try:
                print("Checking if Zoom Meeting requires Registration!")
                WebDriverWait(self.driver, TIME_OUT).until(
                    EC.presence_of_element_located((By.ID, ZOOM_MEETING_REGISTER_DIV_ID)))
            except Exception:
                print("Zoom Meeting doesn't requires Registration!")
                self.capture_ss(ss_name='zoom_meeting_id.png', force=SS_FORCE)
                # add support for: entering passcode
                self.custom_wait(3)
                if self.handle_passcode() is None:
                    return None
                # Now join meeting by url
                self.custom_wait(3)
                self.save_meeting_info({'url': self.driver.current_url})
                print("Got the Zoom Meeting Link! Now trying joining using link!")
                return self.join_meeting_link(self.driver.current_url, True)
            else:
                print("Zoom Meeting requires Registration! We support Basic Registration Only!")
                self.capture_ss(ss_name='zoom_meeting_id.png', force=SS_FORCE)
                if register:
                    if self.basic_register_zoom_meeting(self.driver.current_url):
                        print("Got the Zoom Meeting Link! Now trying joining using link!")
                        return self.join_meeting_link(self.zoom_meeting_url)
                else:
                    self.failed_message = "Zoom Meeting requires Registration! Not registering for the Zoom Meeting!"
                    print(self.failed_message)
                    return False

    # check if bot is in waiting room
    # done | checked > testing pending
    def is_wait_host_page(self, ele_verbose=3, attr_verbose=1):
        # element, label = self.get_element_and_attribute(By.CLASS_NAME, ZOOM_TILE_CLASS, 'Wait Host Page', verbose=2)
        # if label is not None:
        #     if label.lower().find(ZOOM_WAIT_HOST_MSG.lower()) >= 0:
        #         self.capture_ss(ss_name='zoom_meeting_wait_host.png', force=SS_FORCE)
        #         print(ZOOM_WAIT_HOST_MSG)
        #         return True
        # return False
        return self.is_meeting_page(By.CLASS_NAME, ZOOM_TILE_CLASS, 'Wait Host Page', ele_label=ZOOM_WAIT_HOST_MSG,
                                    ss_name='zoom_meeting_wait_host.png', ele_verbose=ele_verbose,
                                    attr_verbose=attr_verbose)

    # check if page contains an err title
    # done | checked > testing pending
    # 'ele_name='Meeting not started Page', attr_name='innerText', ss_name='zoom_meeting_not_started.png'
    # ele_label=ZOOM_MEETING_NOT_STARTED_MSG
    # meeting not started, meeting ended, wait for host to join, req_tok_invalid
    def is_meeting_page(self, locator, selector, ele_name, attr_name='innerText', ss_name='', ele_label='',
                        ele_verbose=0, attr_verbose=0):
        element, label = self.get_element_and_attribute(locator, selector, ele_name=ele_name, attr_name=attr_name,
                                                        ele_verbose=ele_verbose, attr_verbose=attr_verbose)
        ans = element is not None and label is not None and label.lower().strip().find(ele_label.lower().strip()) >= 0
        self.capture_ss(ss_name=ss_name, force=SS_FORCE and ss_name and (True if element else False or ans))
        return element is not None if not attr_name else ans
        # if label is not None:
        #     if label.strip().lower().find(ele_label) >= 0:
        #         return True
        # return False

    # check if meeting not started yet
    # done | checked > testing pending
    def is_zoom_meeting_not_started(self, ele_verbose=3, attr_verbose=1):
        # element, label = self.get_element_and_attribute(By.ID, ZOOM_PROMPT_ID, 'Meeting not started Page', verbose=2)
        # if label is not None:
        #     if label.lower().find(ZOOM_MEETING_NOT_STARTED_MSG.lower()) >= 0:
        #         self.capture_ss(ss_name='zoom_meeting_not_started.png', force=SS_FORCE)
        #         print(ZOOM_MEETING_NOT_STARTED_MSG)
        #         return True
        return self.is_meeting_page(By.ID, ZOOM_PROMPT_ID, 'Meeting not started Page',
                                    ele_label=ZOOM_MEETING_NOT_STARTED_MSG, ss_name='zoom_meeting_not_started.png',
                                    ele_verbose=ele_verbose, attr_verbose=attr_verbose)

    # check if meeting not started yet
    # done | checked > testing pending
    def is_meeting_not_started(self):
        i, tries = 0, 2
        is_not_started = self.is_zoom_meeting_not_started()
        while is_not_started and i < tries:
            # print("inside while loop of not started func")
            self.custom_wait(60)
            is_not_started = self.is_zoom_meeting_not_started(ele_verbose=2, attr_verbose=0)
            # print("waited for 1 min and checked again inside while loop of not started func")
            i += 1
        print(f"i: {i}, tries: {tries}, is_not_started: {is_not_started}")
        try:
            WebDriverWait(self.driver, TIME_OUT).until(
                EC.presence_of_element_located((By.ID, ZOOM_INPUT_NAME_ID)))
        except Exception:
            return False
        else:
            return True

    # join zoom meeting with link
    # not done > testing pending
    def join_meeting_link(self, url, is_opened=False):
        if not is_opened:
            self.open_url(url)
        self.custom_wait()
        self.capture_ss(ss_name='zoom_meeting_link.png', force=SS_FORCE)
        self.custom_wait()
        # press escape to avoid popup of zoom
        pag.press('esc')
        try:
            print("Checking if link can be directly opened with browser!")
            self.action_with_web_driver_wait(By.XPATH, ZOOM_JOIN_BROWSER_XPATH)
        except Exception:
            print("Meeting Link is capable for directly join by browser!")
        else:
            print("Meeting Link is not capable for join by browser! Opening link to be joined by Browser!")
        self.custom_wait(2)
        try:
            self.action_with_web_driver_wait(By.ID, ZOOM_INPUT_NAME_ID, action='keys', keys=self.zoom_name)
        except Exception:
            self.failed_message = "Invalid Meeting Link provided! This Zoom Meeting is not capable for join by browser!"
            print(self.failed_message)
            return False
        else:
            self.capture_ss(ss_name='zoom_meeting_browser_link.png', force=SS_FORCE)
            t1 = time.time()
            meeting_captcha = ReCaptchaV2Cracker(self).crack_captcha(RECAP_CHAL_IFRAME_XPATH)
            t1 = time.time() - t1
            if meeting_captcha is None or meeting_captcha:
                try:
                    self.capture_ss(ss_name='zoom_meeting_recaptcha_defeated.png', force=SS_FORCE)
                    print("Zoom Meeting ReCaptcha is Defeated! Time taken:", str(round(t1, 3)) + 's')
                    self.action_with_web_driver_wait(By.ID, ZOOM_JOIN_BTN_ID)
                    # add support for: entering passcode
                    self.custom_wait(3)
                    if self.handle_passcode() is None:
                        return None
                    # add support for: invalid toked (124) [or other 'error_msg' i.e not comparing msg here]
                    self.custom_wait(3)
                    if self.handle_err_meeting_page():
                        return False
                    # add support for meeting not started
                    self.custom_wait(3)
                    if self.is_meeting_not_started():
                        self.zoom_meeting_not_stared_tries += 1
                        if self.zoom_meeting_not_stared_tries <= 2:
                            print("Zoom Meeting not started yet! Trying Joining Again!")
                            return self.join_meeting_link(self.zoom_meeting_url, True)
                        else:
                            self.failed_message = "Zoom Meeting not started! Zoom Bot couldn't wait more! Check Start" \
                                                " time and Try again!"
                            print(self.failed_message)
                            return None
                    # add support for: Leave Meeting (previously removed by host)
                    self.custom_wait(3)
                    if self.handle_removed_by_host_popup(ZOOM_LEAVE_MEETING_MSG, verbose=3):
                        return None
                    if self.handle_waiting_room(verbose=3):
                        return None
                    self.capture_ss(ss_name='zoom_meeting_success.png', force=SS_FORCE)
                    print("Zoom Meeting is joined Successfully!")
                    return True
                except Exception as err_msg:
                    self.capture_ss(ss_name='zoom_meeting_error_failed.png', force=SS_FORCE)
                    self.failed_message = "Sorry couldn't join Zoom meeting! Error occurred!"
                    print(self.failed_message)
                    print(err_msg)
                    return False
            else:
                self.capture_ss(ss_name='zoom_meeting_failed.png', force=SS_FORCE)
                print("Sorry couldn't join Zoom meeting!")
                return None

    # handle meeting page with error title like 'request token invalid'
    # done | checked > testing pending
    def handle_err_meeting_page(self):
        err_meeting = self.is_meeting_page(By.CLASS_NAME, ZOOM_ERR_MSG_SPAN_CLASS, 'Error Page', attr_name='',
                                           ss_name='zoom_meeting_err.png', ele_verbose=3, attr_verbose=1)
        if err_meeting:
            self.failed_message = "Zoom meeting link has error! Trying joining by ID if ID is provided!"
            print(self.failed_message)
            # print("Zoom meeting link has error! Zoom Bot couldn't proceed! Check meeting link and Try Again!")
            # return False
        return err_meeting

    # handle if bot is in waiting room
    # done | checked > testing pending
    def handle_waiting_room_page(self, ele_verbose=3, attr_verbose=1):
        # i, tries = 0, 6
        # while self.is_wait_host_page() and i < tries:
        t0 = time.time()
        wait_duration = self.zoom_meeting_duration_min
        is_waiting = self.is_wait_host_page(ele_verbose, attr_verbose)
        while is_waiting and int((time.time() - t0) / 60) < wait_duration:
            self.custom_wait(15)
            # self.zoom_meeting_duration_min = wait_duration - int((time.time() - t0) / 60)
            self.zoom_meeting_duration_min = wait_duration - (time.time() - t0) / 60
            is_waiting = self.is_wait_host_page(ele_verbose=2, attr_verbose=0)
            # i += 1
        self.zoom_meeting_duration_min = int(self.zoom_meeting_duration_min)
        if int((time.time() - t0) / 60) >= wait_duration or self.is_wait_host_page(ele_verbose, attr_verbose):
            self.zoom_meeting_duration_min = 0
            self.failed_message = "Host isn't letting Zoom Bot join meeting! Zoom Bot can't wait more! Try Again!"
            print(self.failed_message)
            # return None
            return True
        return False

    # wrapper for handling bot in waiting room
    # done | checked > testing pending
    def handle_waiting_room(self, ele_verbose=3, attr_verbose=1, verbose=0, always_print_checking=False):
        # add support for: please wait host will let you in soon
        self.custom_wait(3)
        waiting_room = self.handle_waiting_room_page(ele_verbose, attr_verbose)
        # add support for: Removed by Host
        self.custom_wait(3)
        waiting_room = waiting_room or self.handle_removed_by_host_popup(verbose=verbose, always_print_checking=
                                                                         always_print_checking)
        # return None in calling func (self.join_meeting_link) if waiting room is True
        if waiting_room:
            return waiting_room
        # add support for: meeting is being recorded
        self.custom_wait(3)
        self.handle_recording_popup(verbose, always_print_checking)
        # add support for: audio/video initial state
        self.custom_wait(3)
        self.disconnect_audio(verbose=verbose)
        return waiting_room

    # check if host removed bot
    # done | checked > testing pending
    def handle_removed_by_host_popup(self, popup_label=ZOOM_REMOVED_BY_HOST_MSG, verbose=0,
                                     always_print_checking=False):
        removed_by_host = self.is_meeting_popup(popup_label, verbose, always_print_checking)
        if removed_by_host:
            self.close_meeting_popup(verbose=verbose, always_print_checking=always_print_checking)
            message = 'previously ' if popup_label == ZOOM_LEAVE_MEETING_MSG else ''
            self.failed_message = f"Zoom Bot isn't allowed to join meeting as it was {message}removed by Host! " \
                                  f"Try Again!"
            print(self.failed_message)
            # return None
        return removed_by_host

    # handle recording popup
    # done | checked > testing pending
    def handle_recording_popup(self, verbose=0, always_print_checking=False):
        recording_popup = self.is_meeting_popup(ZOOM_MEETING_RECORDED_MSG, verbose, always_print_checking)
        if recording_popup:
            self.close_meeting_popup(btn_ind=1, verbose=verbose, always_print_checking=always_print_checking)
        return recording_popup

    # handle passcode entering for meeting
    # done | checked > testing pending
    def handle_passcode(self):
        enter_passcode = self.enter_passcode()
        if enter_passcode:
            self.action_with_web_driver_wait(By.ID, ZOOM_JOIN_BTN_ID)
            self.custom_wait(3)
            err_element, _ = self.get_element_and_attribute(By.XPATH, ZOOM_INVALID_PASS_XPATH, 'passcode_invalid', '')
            if err_element is not None:
                self.failed_message = "Couldn't join meeting! Invalid Meeting passcode is provided!"
                print(self.failed_message)
                return None
        return enter_passcode

    # enter passcode for meeting
    # done | checked > testing pending
    def enter_passcode(self):
        try:
            print("Checking if passcode can be entered!")
            pass_code, _ = self.get_element_and_attribute(By.ID, ZOOM_INPUT_PASS_ID, 'passcode_input', '', ele_verbose=1)
            if pass_code is None:
                raise Exception
            elif not self.zoom_meeting_pass:
                self.failed_message = "Meeting requires passcode! Can't enter passcode as it is not provided!"
                print(self.failed_message)
                return None
            else:
                self.action_with_web_driver_wait(By.ID, ZOOM_INPUT_PASS_ID, action='key', keys=self.zoom_meeting_pass)
        except Exception:
            print("No input is found for entering the passcode!")
            return False
        else:
            print("Passcode is entered Successfully!")
            return True

    # done | checked > testing pending
    # IMP NOTE: ZOOM FOOTER contains all important buttons like mute/ unmute/ chat/ etc. It kept becoming invisible
    # so, below function freezes it to avoid Selenium's: Element is not intractable error.
    def freeze_zoom_footer(self):
        try:
            self.driver.execute_script(FREEZE_ZOOM_FOOTER_SCRIPT, ZOOM_FOOTER_ID)
        except Exception as err_msg:
            print("Couldn't Freeze Zoom Footer! Error occurred!")
            print(err_msg)
            return False
        else:
            return True

    # connect audio for bot
    # done | checked > testing pending
    def connect_audio(self):
        self.freeze_zoom_footer()
        try:
            WebDriverWait(self.driver, TIME_OUT).until(
                EC.presence_of_element_located((By.CLASS_NAME, ZOOM_JOIN_AUDIO_BTN_CLASS)))
        except Exception:
            audio_btn, audio_label = self.get_element_and_attribute(By.CLASS_NAME, ZOOM_AUDIO_BTN_CLASS, 'Audio Btn',
                                                                    'aria-label', ele_verbose=2, attr_verbose=2)
            if audio_label is not None:
                if audio_label.lower() == ZOOM_JOIN_AUDIO_LABEL.lower():
                    # make element intractable: freeze footer
                    audio_btn.click()
                    self.custom_wait()
                    # self.action_with_web_driver_wait(By.CLASS_NAME, ZOOM_JOIN_AUDIO_BTN_CLASS)
                    self.driver.execute_script('arguments[0].click();', WebDriverWait(self.driver, TIME_OUT).until(
                        EC.presence_of_element_located((By.CLASS_NAME, ZOOM_JOIN_AUDIO_BTN_CLASS))))
                    print("Audio is Connected Successfully!")
                else:
                    print("Audio is already Connected!")
                return True
            return False
        else:
            self.action_with_web_driver_wait(By.CLASS_NAME, ZOOM_JOIN_AUDIO_BTN_CLASS)
            print("Audio is Connected Successfully!")
            return True

    # disconnect audio for bot
    # done | checked > testing pending
    def disconnect_audio(self, verbose=3):
        self.freeze_zoom_footer()
        try:
            WebDriverWait(self.driver, TIME_OUT).until(
                EC.presence_of_element_located((By.CLASS_NAME, ZOOM_JOIN_AUDIO_BTN_CLASS)))
        except Exception:
            try:
                # make element intractable: freeze footer
                self.action_with_web_driver_wait(By.ID, ZOOM_AUDIO_OPTIONS_ID)
                self.action_with_web_driver_wait(By.XPATH, ZOOM_LEAVE_AUDIO_XPATH)
                self.action_with_web_driver_wait(By.CLASS_NAME, ZOOM_AUDIO_BTN_CLASS)
            except Exception as err_msg:
                audio_btn, audio_label = self.get_element_and_attribute(By.CLASS_NAME, ZOOM_AUDIO_BTN_CLASS, 'Audio Btn'
                                                                        , 'aria-label', ele_verbose=2, attr_verbose=2)
                if audio_label is not None:
                    if audio_label.lower() == ZOOM_JOIN_AUDIO_LABEL.lower():
                        # if verbose == 1 or verbose >= 3:
                        if verbose == 2 or verbose >= 3:
                            print("Audio is already Disconnected!")
                        return True
                    if verbose == 2 or verbose >= 3:
                        print("Couldn't disconnect Audio! Error occurred!")
                        print(err_msg)
                    return False
                return False
            else:
                if verbose == 1 or verbose >= 3:
                    print("Audio is Disconnected Successfully!")
                return True
        else:
            # if verbose == 1 or verbose >= 3:
            if verbose == 2 or verbose >= 3:
                print("Audio is already Disconnected!")
            # make element intractable: freeze footer
            self.action_with_web_driver_wait(By.CLASS_NAME, ZOOM_AUDIO_BTN_CLASS)
            return True

    # mute or mute audio for bot, audio will be connected first if join_audio=True
    # done | checked > testing pending
    def mute_unmute_audio(self, label=ZOOM_MUTE_LABEL, join_audio=True):
        self.freeze_zoom_footer()
        connected_audio = True
        if join_audio:
            connected_audio = self.connect_audio()
        if connected_audio:
            audio_btn, audio_label = self.get_element_and_attribute(By.CLASS_NAME, ZOOM_AUDIO_BTN_CLASS, 'Audio Btn',
                                                                    'aria-label', ele_verbose=2, attr_verbose=2)
            if audio_label is not None:
                if audio_label.lower() == 'Join'.lower():
                    print("Invalid Mic is connected! Connect valid mic first!")
                    return False
                elif not join_audio and audio_label.lower() == ZOOM_JOIN_AUDIO_LABEL.lower():
                    print("Audio is not connected! Not joining it and thus already on",
                          label.strip().split(' ')[0].lower() + '!')
                elif audio_label.lower() != label.strip().lower():
                    print("Audio is already on", label.strip().split(' ')[0].lower() + '!')
                else:
                    # make element intractable: freeze footer
                    audio_btn.click()
                    print("Audio is", label.strip().split(' ')[0].lower() + 'd', "Successfully!")
                return True
            return False

    # start/ stop video for bot
    # done | checked > testing pending
    def start_stop_video(self, label=ZOOM_STOP_VIDEO_LABEL):
        self.freeze_zoom_footer()
        video_btn, video_label = self.get_element_and_attribute(By.CLASS_NAME, ZOOM_VIDEO_BTN_CLASS, 'Video Btn',
                                                                'aria-label', ele_verbose=2, attr_verbose=2)
        if video_label is not None:
            if video_label.lower() != label.strip().lower():
                print("Video is already on", label.strip().split(' ')[0].lower() + '!')
            else:
                # make element intractable: freeze footer
                video_btn.click()
                print("Video is", label.strip().split(' ')[0].lower() + 'ed', "Successfully!")
            return True
        return False

    # check if any popup with given label exits
    # done | checked > testing pending
    def is_meeting_popup(self, label=ZOOM_MEETING_RECORDED_MSG, verbose=0, always_print_checking=False):
        checking_msg = f"Checking Popup for: '{label}'!"
        if always_print_checking:
            print(checking_msg)
        popup, popup_label = self.get_element_and_attribute(By.CLASS_NAME, ZOOM_POPUP_TITLE_DIV, 'Popup')
        if popup_label is not None:
            if popup_label.lower() == label.lower():
                self.capture_ss(ss_name=f"meeting_{label.strip().split(' ')[-1]}_popup.png", force=SS_FORCE)
                if verbose == 1 or verbose >= 3:
                    print(checking_msg + '\n' if not always_print_checking else '',
                          f"Popup containing: '{label} is found!'", sep='')
                return True
            if verbose == 2 or verbose >= 3:
                print(checking_msg + '\n' if not always_print_checking else '', f"Popup doesn't contain: '{label}'!",
                      sep='')
            return False
        if popup is None and (verbose == 2 or verbose >= 3):
            # print(checking_msg + '\n' if not always_print_checking else '', f"There is no Popup for: '{label}'!", sep='')
            print(f"There is no Popup for: '{label}'!")
        return False

    # close popup with given index of button
    # done | checked > testing pending
    def close_meeting_popup(self, btn_ind=0, verbose=0, always_print_checking=False):
        closing_msg = "Closing Meeting popup!"
        if always_print_checking:
            print(closing_msg)
        try:
            self.action_with_web_driver_wait(By.CSS_SELECTOR, 'div.' + ZOOM_POP_BUTTONS_DIV + ' > button',
                                             index=btn_ind)
        except Exception as err_msg:
            if verbose == 2 or verbose >= 3:
                print(closing_msg + ' ' if not always_print_checking else '',
                      "Couldn't close the popup! Error occurred!", sep='')
            print(err_msg)
            return False
        else:
            if verbose == 1 or verbose >= 3:
                print(closing_msg + ' ' if not always_print_checking else '', "Popup is closed Successfully!", sep='')
            return True

    # check if meeting is finished
    # done | checked > testing pending
    def is_meeting_ended(self, leave=True, verbose=0, always_print_checking=False):
        host_ended = self.is_meeting_popup(ZOOM_MEETING_ENDED_MSG, verbose, always_print_checking)
        self.capture_ss(ss_name='zoom_meeting_ended.png', force=SS_FORCE and host_ended)
        if host_ended and leave:
            self.close_meeting_popup(verbose=verbose, always_print_checking=always_print_checking)
        return host_ended

    # leave meeting by bot
    # done | checked > testing pending
    def leave_meeting(self):
        print("Checking if Zoom Meeting is already finished!")
        meeting_finished = self.is_meeting_page(By.CLASS_NAME, ZOOM_MEETING_FINISHED_CLASS, 'Meeting Finished Page',
                                                ss_name='zoom_meeting_finished.png', attr_name='', ele_verbose=3,
                                                attr_verbose=1)
        if meeting_finished:
            print("Zoom Meeting is already finished!")
            return meeting_finished
        host_ended = self.is_meeting_ended(leave=False)
        if not host_ended:
            print("Host has not ended the meeting yet!")
            self.freeze_zoom_footer()
            try:
                # make element intractable: freeze footer
                self.action_with_web_driver_wait(By.CLASS_NAME, ZOOM_FOOTER_LEAVE_BTN_CLASS)
                self.action_with_web_driver_wait(By.CLASS_NAME, ZOOM_LEAVE_MEETING_BTN_CLASS)
            except Exception:
                print("Couldn't leave meeting! Error occurred!")
                return False
            else:
                print("Left the meeting successfully!")
                return True
        else:
            print("Host has ended the meeting!")
            self.close_meeting_popup()
            print("Left the meeting successfully!")
            return True

    # send msg to given receiver: to
    # done | checked > testing pending
    def send_msg_on_chatbox(self, to='host', msg=ZOOM_CHAT_MSG_HOST):
        self.freeze_zoom_footer()
        try:
            print("Opening chatbox!")
            # make element intractable: freeze footer
            self.action_with_web_driver_wait(By.CLASS_NAME, ZOOM_CHATBOX_ICON_CLASS)
            self.action_with_web_driver_wait(By.ID, ZOOM_CHAT_MENU_ID)
            print("Extracting receivers!")
            receivers_elements = WebDriverWait(self.driver, TIME_OUT).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, ZOOM_CHAT_MENU_RECEIVERS_CLASS)))
            # for below, innerText will work not innerHTML
            receivers = [self.get_ele_attr(receiver) for receiver in receivers_elements]
            ind = -1
            for i, receiver in enumerate(receivers):
                if (ind == -1 and receiver.lower().find('everyone') >= 0) or (receiver.lower().find(to.lower()) >= 0):
                    ind = i
                print(f'{i + 1}: {receiver}')
            print("Selected receiver:", receivers[ind], "Given receiver:", to)
            receivers_elements[ind].click()
            print("Writing and sending message on chatbox!")
            self.action_with_web_driver_wait(By.CLASS_NAME, ZOOM_CHATBOX_CLASS, action='keys', keys=msg)
            self.action_with_web_driver_wait(By.CLASS_NAME, ZOOM_CHATBOX_CLASS, action='keys', keys=Keys.ENTER)
            # make element intractable: freeze footer
            self.action_with_web_driver_wait(By.CLASS_NAME, ZOOM_CHATBOX_ICON_CLASS)
            print("Message is send Successfully!")
        except Exception as err_msg:
            print("Couldn't send message on chatbox to:", to, "Error occurred!")
            print(err_msg)
            return False
        else:
            return True

    # save/ extract chats info
    # done | checked > testing pending
    def extract_all_chats(self):
        self.freeze_zoom_footer()
        try:
            print("Opening chatbox!")
            # make element intractable: freeze footer
            self.action_with_web_driver_wait(By.CLASS_NAME, ZOOM_CHATBOX_ICON_CLASS)
            print("Extracting chats!")
            chats_elements = WebDriverWait(self.driver, TIME_OUT).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, ZOOM_CHAT_MSG_CLASS)))
            chats = [self.get_ele_attr(chat) for chat in chats_elements]
        except Exception as err_msg:
            # make element intractable: freeze footer
            self.action_with_web_driver_wait(By.CLASS_NAME, ZOOM_CHATBOX_ICON_CLASS)
            print("Couldn't find chats! No chats are found!")
            print(err_msg)
            return False
        else:
            # make element intractable: freeze footer
            self.action_with_web_driver_wait(By.CLASS_NAME, ZOOM_CHATBOX_ICON_CLASS)
            if not chats:
                print("No chats are found!")
                return False
            chats_info = ''
            for i, chat in enumerate(chats):
                chats_info += f'{i + 1}: {chat}\n'
                print(f'{i + 1}: {chat}')
            return save_info(chats_info, gen_path(self.bot_root, 'chats_info.txt'), info_name='Chats Info')

    # save/ extract and capture participants info
    # done | checked > testing pending
    def extract_all_participants(self, ss_name='zoom_attendance_attending.png'):
        self.freeze_zoom_footer()
        try:
            print("Opening participants box!")
            # make element intractable: freeze footer
            self.action_with_web_driver_wait(By.CLASS_NAME, ZOOM_PARTICIPANTS_ICON_CLASS)
            self.capture_ss(ss_name=ss_name, append_time=False, force=SS_FORCE and ss_name)
            print("Extracting participants!")
            participants_elements = WebDriverWait(self.driver, TIME_OUT).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, ZOOM_PARTICIPANTS_LI_CLASS)))
            # below also provides audio/ video status along with participant name (i.e aria-label attribute)
            # participants = [self.get_ele_attr(participant, 'aria-label') for participant in participants_elements]
            participants = [self.get_ele_attr(participant).split('\n')[0].strip() for participant in
                            participants_elements]
        except Exception as err_msg:
            # make element intractable: freeze footer
            self.action_with_web_driver_wait(By.CLASS_NAME, ZOOM_PARTICIPANTS_ICON_CLASS)
            print("Couldn't find participants! No participants are found!")
            print(err_msg)
            return False
        else:
            # make element intractable: freeze footer
            self.action_with_web_driver_wait(By.CLASS_NAME, ZOOM_PARTICIPANTS_ICON_CLASS)
            if not participants:
                print("No participants are found!")
                return False
            participants_info = ''
            for i, participant in enumerate(participants):
                participants_info += f'{i + 1}: {participant}\n'
                print(f'{i + 1}: {participant}')
            return save_info(participants_info, gen_path(self.bot_root, 'participants_info.txt'), info_name='Participants Info')

    # save/ extract invite info
    # done | checked > testing pending
    def extract_invite_info(self):
        invite, invite_label = self.get_element_and_attribute(By.ID, ZOOM_INVITE_INFO_ID, 'Meeting Info')
        if invite_label is not None:
            if invite_label:
                print("Zoom Meeting Invite Info: ", invite_label)
                return save_info(invite_label, gen_path(self.bot_root, 'invite_info.txt'), info_name='Invite Info')
            print("No Zoom Meeting info is found!")
            return False
        print("Couldn't find meeting info! Error occurred!")
        return False

    # generate email subject and message for sending email
    # done | checked > testing pending
    def gen_email_sub_msg(self, mode='started'):
        log_message = self.failed_message[:] if mode == 'failed' else f"Zoom Bot {mode} attended meeting!"
        email_sub = f"[{mode.upper()}] Zoom Bot has {mode} attending your Zoom Meeting: " \
                    f"{self.zoom_meeting_id if self.zoom_meeting_id else self.zoom_meeting_tag}"
        email_msg_header = f'Dear {self.name}\n\n{email_sub.split("]")[-1].strip()} [{self.zoom_meeting_tag}] at ' \
                           f'{get_formatted_date_time()}.\n\n'
        email_msg_body = f'Zoom Name: {self.zoom_name}\nZoom Email: {self.zoom_email}\nZoom Meeting Tag: ' \
                         f'{self.zoom_meeting_tag}\nZoom Meeting ID: {self.zoom_meeting_id}\nZoom Meeting Link: ' \
                         f'{self.zoom_meeting_url}\n\nLog Message: "{log_message}"\n\n' \
                         f'PFA screenshot(s)/ file(s) for the same!\n\nThanks a lot for using Our Zoom Bot!\n\n'
        email_msg_footer = f'NOTE: This email is sent using Zoom Bot Python Script [CLOUD] which is Developed with ❤️' \
                           f' by: {NAME}, a {YEAR} Year Undergraduate from {DEPARTMENT} Department at {CLG}\n\n'
        email_msg_footer += f'*** Copyright © 2021 Zoom Bot | {NAME} | All Rights Reserved ***\n\n'
        email_msg = email_msg_header + email_msg_body + email_msg_footer
        return email_sub, email_msg

    # generate email attachments/ files for sending email
    # done | checked > testing pending
    def gen_email_attachment(self, mode='started', ss_name='', is_owner=False):
        filenames = ['logs.txt'] if is_owner else []
        filenames += ['invite_info.txt', 'participants_info.txt', 'chats_info.txt', 'registration_info.txt']
        files = [gen_path(self.bot_root, filename) for filename in filenames]
        if is_owner:
            os.system(f'rm -f {gen_path(self.bot_root, "screenshots.zip")}')
            make_archive(gen_path(self.bot_root, "screenshots"), "zip", self.ss_dir)
            files += [gen_path(self.bot_root, "screenshots.zip")]
        valid_files = [filepath for filepath in files if validate_path(filepath)]
        email_zip_filename = f'{self.zoom_meeting_id if self.zoom_meeting_id else self.zoom_meeting_tag}_' \
                             f'{get_formatted_date_time()}_{mode}.zip'
        email_zip_filepath = gen_path(self.bot_root, email_zip_filename)
        email_files = []
        if valid_files:
            save_zip(email_zip_filepath, valid_files, mode='w', filename=email_zip_filename)
            email_files += [email_zip_filepath]
        # files = [f'{self.ss_dir}/zoom_bot_{mode}.png']
        files = [gen_path(self.ss_dir, ss_name)] if ss_name else []
        files += [gen_path(self.ss_dir, 'zoom_attendance_attending.png')] if mode == 'finished' else []
        email_files += [filepath for filepath in files if validate_path(filepath)]
        return email_files

    # send email for given mode and ss
    # done | checked > testing pending
    def send_email(self, mode='started', ss_name='', is_owner=False):
        # get email sub, msg and files
        email_sub, email_msg = self.gen_email_sub_msg(mode)
        email_files = self.gen_email_attachment(mode=mode, ss_name=ss_name, is_owner=is_owner)
        # init Gmail API Class
        gmail_api = SendEmail(EMAIL_FROM, self.email, email_sub, email_msg, email_files, EMAIL_CC, EMAIL_BCC)
        # send email
        gmail_api.send_email_with_gmail_api()

    # extract info and send email if notify=True for given mode
    # done | checked > testing pending
    def extract_info_breakpoint(self, mode='started', notify=True):
        if notify:
            ss_name = f'zoom_bot_{mode}_{get_formatted_date_time()}.png'
            print(f"Zoom Bot has {mode} attending this Zoom Meeting!")
            self.capture_ss(ss_name=ss_name, append_time=False, force=SS_FORCE)
        if mode == 'started':
            self.extract_invite_info()
        # if mode != 'failed': <- This always creates errors since info isn't available when meeting is finished
        if mode in ['started', 'attending']:
            self.extract_all_participants(ss_name=f'zoom_attendance_{mode}.png')
            self.extract_all_chats()
        if self.email_notify and notify:
            self.send_email(mode=mode, ss_name=ss_name, is_owner=self.is_owner)

    # capture attendance (extract and capture participants info)
    # done | checked > testing pending
    def capture_attendance(self):
        # self.extract_all_participants()
        # self.extract_all_chats()
        self.extract_info_breakpoint(mode='attending', notify=False)
        # self.action_with_web_driver_wait(By.CLASS_NAME, ZOOM_PARTICIPANTS_ICON_CLASS)
        # self.custom_wait()
        # self.capture_ss(ss_name=f'zoom_attendance.png', append_time=False, force=SS_FORCE)
        # self.action_with_web_driver_wait(By.CLASS_NAME, ZOOM_PARTICIPANTS_ICON_CLASS)

    # start Zoom Bot for attending meeting
    # not done | not checked > testing pending
    def start_bot(self):
        try:
            is_joined, attendance_taken = False, False
            if self.zoom_meeting_url:
                is_joined = self.join_meeting_link(self.zoom_meeting_url)
            elif is_joined is not None and not is_joined and self.zoom_meeting_id:
                is_joined = self.join_meeting_id(register=self.first_name and self.last_name and self.register_email)
            elif is_joined is None:
                self.extract_info_breakpoint('failed')
                return False
            if is_joined:
                t0 = time.time()
                self.extract_info_breakpoint('started')
                half_duration_min = int(self.zoom_meeting_duration_min / 2)
                while int((time.time() - t0) / 60) < self.zoom_meeting_duration_min:
                    self.custom_wait(30)
                    # capture ss/ take attendance at Half duration
                    if not attendance_taken and abs(int((time.time() - t0) / 60) - half_duration_min) <= 5:
                        self.capture_attendance()
                        attendance_taken = True
                    # check if host removed from meeting or ended the meeting or added bot to waiting room
                    if self.handle_removed_by_host_popup(verbose=1) or self.is_meeting_ended(leave=False, verbose=1) \
                            or self.handle_waiting_room(ele_verbose=1, attr_verbose=1, verbose=1):
                        break
                self.custom_wait(5)
                self.leave_meeting()
                print("Zoom Meeting was attended for duration:", str(int((time.time() - t0) / 60)) + ' min',
                      'and actual Duration:', str(self.zoom_meeting_duration_min) + ' min')
                self.extract_info_breakpoint('finished')
                return True
            else:
                self.extract_info_breakpoint('failed')
                return False
        except Exception as err_msg:
            self.extract_info_breakpoint('failed')
            print(err_msg)
            return False

    # wrapper for quiting the Zoom Bot
    # done | checked
    def quit_bot(self):
        try:
            self.quit_driver()
        except Exception as err_msg:
            print("Couldn't Quit the Zoom Bot! Error occurred!")
            print(err_msg)
            return False
        else:
            print("Quit the Zoom Bot Successfully!")
            return True


# Build Base Chrome Profile
def build_base_chrome_profile(base_profile_root, base_profile_dir, is_headless=True):
    os.system(f'rm -rf {base_profile_root}')
    print(f"Building Base Chrome Profile!")
    browser = Browser(is_headless, profile_root=base_profile_root, profile_dir=base_profile_dir)
    browser.browse()
    print(f"Base Chrome Profile is built Successfully!")


# Build Chrome Profile
def build_chrome_profile(user_id, base_profile_root, base_profile_dir, profile_dir, is_headless=True):
    if not validate_path(base_profile_root) or not validate_path(base_profile_dir):
        print(f"Base Chrome Profile for {user_id} doesn't Exist!")
        build_base_chrome_profile(base_profile_root, base_profile_dir, is_headless)
    print(f"Building Chrome Profile for {user_id}! Removing Old and Building new by Copying Base Profile!")
    os.system(f'rm -rf {profile_dir}')
    os.system(f'cp -r {base_profile_dir}/ {profile_dir}')
    print(f"Chrome Profile for {user_id} is built Successfully!")


# Main
def main(argv):
    if len(argv) == 1 or not argv[1] or not validate_path(argv[1]):
        print("kwargs_path isn't validated or not supplied! Exiting!")
        return 1
    kwargs_path = argv[1]
    kwargs = json.load(open(kwargs_path, 'r'))
    users_path = kwargs.get('users_path', '')
    print(f'users_path: {users_path}\nkwargs_path: {kwargs_path}')
    if not validate_path(users_path):
        print("users_path isn't supplied or not validated! Exiting!")
        return 2
    user_id, meeting_index, meeting_name = kwargs.get('id', None), kwargs.get('index', ''), kwargs.get('zoom_name', '')
    print(f'user_id: {user_id}, meeting_index: {meeting_index}, meeting_name: {meeting_name}')
    if not user_id or (meeting_index is None or meeting_index == '') or not meeting_name:
        print("user_id or meeting_index or meeting_name isn't supplied! Exiting!")
        return 3
    meeting_id, meeting_url = kwargs.get('meeting_id', ''), kwargs.get('url', '')
    print(f'meeting_id: {meeting_id}\nmeeting_url: {meeting_url}')
    if not meeting_id and not meeting_url:
        print("Both meeting_id and meeting_url aren't supplied! Exiting!")
        return 4
    users_dict = json.load(open(users_path, 'r'))
    cancel = get_meeting_dict_info('cancel', users_dict=users_dict, user_id=user_id, meeting_index=meeting_index,
                                   default=True)
    if cancel:
        print("User has cancelled the scheduled Meeting! Exiting!")
        return 5
    base_profile_root, base_profile_dir = kwargs.get('base_profile_root', ''), kwargs.get('base_profile_dir', '')
    print(f'base_profile_root: {base_profile_root}\nbase_profile_dir: {base_profile_dir}')
    if not validate_path(base_profile_root) or not validate_path(base_profile_dir):
        print("base_profile_root or base_profile_dir isn't supplied or not validated! Exiting!")
        return 6
    profile_root, profile_dir = kwargs.get('profile_root', ''), kwargs.get('profile_dir', '')
    print(f'profile_root: {profile_root}\nprofile_dir: {profile_dir}')
    if not validate_path(profile_root) or not validate_path(profile_dir):
        print("profile_root or profile_dir isn't supplied or not validated! Exiting!")
        return 7
    # Build chrome profile from base chrome profile
    build_chrome_profile(user_id, base_profile_root, base_profile_dir, profile_dir)
    # Init Zoom Bot
    zoom_bot = ZoomBot(IS_HEADLESS, **kwargs)
    try:
        zoom_bot.start_bot()
        # print("testing")
        zoom_bot.quit_bot()
    except Exception as err_msg:
        print("Error occurred inside of Bot! Quiting Bot")
        print(err_msg)
        try:
            zoom_bot.quit_driver()
            # print('testing')
        except Exception as err_msg:
            print("Error occurred in Quiting the Driver!")
            print(err_msg)
    else:
        # copy screenshots to bot root dir
        os.system(f'cp -r {zoom_bot.ss_dir}/ {zoom_bot.bot_root}/screenshots')
    finally:
        # to save space on VM, delete chrome profile as it can be rebuilt quickly (tradeoff between space & time)
        os.system(f'rm -rf {profile_root}')
        print(f"Chrome Profile for {user_id} is removed Successfully!")
        # raise Exception


if __name__ == '__main__':
    main(sys.argv)
    # main(['', '/Users/umeshyadav/Desktop/azure_zoom/users/2018ucs0078/5875109727_11-06-2021/kwargs.json'])
    # script()

# solver = ZoomBot(False)
# # solver.crack_captcha()
# # solver.login_zoom()
#
# while True:
#     task = input('what to do: ')
#     if task == 'join':
#         meet = solver.join_meeting_link()
#     elif task == 'mute':
#         mute = solver.mute_unmute_audio()
#     elif task == 'unmute':
#         mute = solver.mute_unmute_audio(ZOOM_UNMUTE_LABEL)
#     elif task == 'connect':
#         connect = solver.connect_audio()
#     elif task == 'disconnect':
#         connect = solver.disconnect_audio()
#     elif task == 'stop':
#         stop = solver.start_stop_video()
#     elif task == 'start':
#         stop = solver.start_stop_video(ZOOM_START_VIDEO_LABEL)
#     elif task == 'host':
#         print("Checking if host has ended the meeting!")
#         host_ended = solver.is_meeting_popup(ZOOM_MEETING_ENDED_MSG)
#         if not host_ended:
#             print("Host has not ended the meeting yet!")
#     elif task == 'leave':
#         leave = solver.leave_meeting()
#     elif task == 'msg':
#         msg = solver.send_msg_on_chatbox()
#     elif task == 'msg_every':
#         msg = solver.send_msg_on_chatbox(to='everyone', msg=ZOOM_CHAT_MSG_EVERYONE)
#     elif task == 'extract':
#         chats = solver.extract_all_chats()
#     elif task == 'info':
#         info = solver.extract_invite_info()
#     elif task == 'attendance':
#         att = solver.extract_all_participants()
#     elif task == 'quit':
#         solver.quit_driver()
#     elif task == 'exit':
#         try:
#             solver.quit_driver()
#         except Exception:
#             pass
#         break
#     else:
#         print("Wrong Entry! Retry")
