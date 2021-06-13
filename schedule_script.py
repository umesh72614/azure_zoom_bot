# Selenium Web Driver
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.chrome.options import Options
# Others
import pickle
import time
from constants import *
from pprint import pprint
from utilities import *

"""
NOTE: If you are joining zoom by browser and you successfully joined it but closed the window/ tab without leaving
the meeting, then, you will still be shown available on the meeting for some minutes (about 1-2)!! So be careful while 
joining browser meetings of zoom, if you are not logged in or not saving cookies and you close browser in between, 
you will still be present in the meeting for few minutes!!
NOTE: Helpful crontab tool: https://crontab.guru/ and https://cronitor.io/
NOTE: Chromedriver doesn't stores history in Headless (saves only in Head mode) Mode but it does stores cookies in 
both head and headless mode.
"""


# Chrome Driver
class ChromeDriver:
    # init
    def __init__(self, is_headless, **kwargs):
        # want headless -> if true then only print else won't print
        self.is_headless = is_headless
        # screenshot
        self.profile_root = kwargs.get('profile_root', f'{os.getcwd()}')
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


# Build Base Chrome Profile: History is not saved by chromedriver in headless mode, only cookies are saved!
def build_base_chrome_profile(base_profile_root, base_profile_dir, is_headless=True):
    os.system(f'rm -rf {base_profile_root}')
    print(f"Building Base Chrome Profile!")
    browser = Browser(is_headless, profile_root=base_profile_root, profile_dir=base_profile_dir)
    browser.browse()
    print(f"Base Chrome Profile is built Successfully!")


# Script
def script(root=os.getcwd()):
    user_dir_root = gen_path(root, 'users', make_path_dir=True)
    users_path = gen_path(root, 'users.json')
    if not validate_path(users_path):
        print("users_path is not validated! Exiting!")
        return 1
    users = json.load(open(users_path, 'r'))
    # pprint(users)
    kwargs = {}
    for user_id in users:
        user_dir = gen_path(user_dir_root, user_id)
        base_profile_root = gen_path(root, 'base_chrome')
        base_profile_dir = gen_path(base_profile_root, 'base_chrome_profile')
        if not validate_path(base_profile_root) or not validate_path(base_profile_dir):
            # ChromeDriver already includes os.makedirs/ gen_path, so not including it here
            build_base_chrome_profile(base_profile_root, base_profile_dir)
        else:
            print("Base Chrome Profile already exists!")
        meetings = users[user_id]['zoom']['meetings']
        for index, meeting in enumerate(meetings):
            current_date, start_date = get_formatted_date(), meeting['schedule']['start_date']
            meeting_dir = gen_path(user_dir, f'{meeting["id"] if meeting["id"] else meeting["tag"]}_{current_date}',
                                   make_path_dir=True)
            profile_root = gen_path(meeting_dir, 'chrome', make_path_dir=True)
            profile_dir = gen_path(profile_root, 'chrome_profile', make_path_dir=True)
            kwargs_path = gen_path(meeting_dir, 'kwargs.json')
            pprint(meeting)
            kwargs.update({
                # Chrome Driver
                'profile_root': profile_root,
                'profile_dir': profile_dir,
                # Zoom Credentials
                'zoom_email': users[user_id]['zoom'].get('email', ''),
                'zoom_pass': users[user_id]['zoom'].get('pass', ''),
                # Zoom Meeting
                'meeting_id': meeting.get('id', ''),
                'meeting_pass': meeting.get('pass', ''),
                'zoom_name': meeting.get('name', ''),
                'tag': meeting.get('tag', 'Bot Meeting'),
                'url': meeting.get('url', ''),
                'index': index,
                'duration': meeting['schedule'].get('duration', '00:15'),
                'cancel': meeting.get('cancel', False),
                # Zoom Meeting Registration
                'f_name': meeting.get('registration', {}).get('f_name', meeting.get('name', '').split(' ')[0].strip()),
                'l_name': meeting.get('registration', {}).get('l_name', meeting.get('name', '').split(' ')[-1].strip()),
                'register_email': meeting.get('registration', {}).get('email', users[user_id]['zoom'].get('email', '')),
                # GMail
                'id': user_id,
                'email': users[user_id]['email'],
                'name': users[user_id]['name'],
                'email_notify': meeting.get('email_notify', False),
                # 'email_notify': False,
                'owner': users[user_id].get('owner', False),
                # Zoom Bot
                'bot_root': meeting_dir,
                'users_path': users_path,
                'base_profile_root': base_profile_root,
                'base_profile_dir': base_profile_dir,
                'kwargs_path': kwargs_path,
            })
            pprint(kwargs)
            json.dump(kwargs, open(kwargs_path, 'w'), indent=4)
            script_path = gen_path(root, 'zoom_bot.py')
            logs_path = gen_path(meeting_dir, 'logs.txt')
            if meeting.get('repeat'):
                end_date, weekdays = meeting['schedule']['end_date'], meeting['schedule']['weekdays']
                # os.system(f'python3 zoom_bot.py "{kwargs_path}"')
                # os.system(f'python3 zoom_bot.py {kwargs_path} >{root_dir}/logs.txt')
                # os.system(f'python3 zoom_bot.py {kwargs_path} >{root_dir}/logs.txt 2>&1')
                # if current date falls between start and end date then check for weekday and time and then schedule
                # reference: Benefit of having dates in format: YYYY-MM-DD : https://stackoverflow.com/a/16166356
                if start_date <= current_date <= end_date:
                    # in users.json: # 0 -> sun, 6 -> sat but here in datetime.date.weekday(): # 0 -> mon, 6 -> sun
                    # print("Meeting is scheduled today!")
                    current_weekday = (datetime.now().weekday() + 1) % 7
                    if current_weekday in weekdays:
                        print(f"Meeting: "
                              f"{meeting.get('id', '') if meeting.get('id', '') else meeting.get('tag', 'SBP100')} "
                              f"is scheduled today!")
                        os.system(f'python3 {script_path} {kwargs_path} >{logs_path} 2>&1')
                        # os.system(f'python3 zoom_bot.py {kwargs_path} > {root_dir}/logs.txt')
                        # # if start_time + duration < duration + 10 min then schedule
                        # start_time, duration = meeting['schedule']['start_time'], meeting['schedule']['duration']
                        # cron_job = f'#{user_id}_{meeting["id"]}_{meeting["tag"]}_{index}_{meeting["last_scheduled"]}'
                        # cron_job = f'{cron_job}\n{minute} {hour} {current_day} {current_month} {current_weekday}'
                        # cron_job = f'{cron_job} python3 {script_path} {kwargs_path} >{logs_path} 2>&1'
                        # cron_job = f"{cron_job} ; crontab -l | grep -iv '{cron_job}' | crontab -"
                        # cron_job = f'(crontab -l 2>/dev/null || true ; echo "{cron_job}") | crontab -'
                        # os.system(cron_job)
                    else:
                        print(f"Sorry! Meeting: "
                              f"{meeting.get('id', '') if meeting.get('id', '') else meeting.get('tag', 'SBP100')} "
                              f"isn't scheduled today!")
                        os.system(f'rm -rf {meeting_dir}')
                else:
                    print(f"Sorry! Meeting: "
                          f"{meeting.get('id', '') if meeting.get('id', '') else meeting.get('tag', 'SBP100')} "
                          f"isn't scheduled today!")
                    os.system(f'rm -rf {meeting_dir}')
            else:
                # check if current date equals start date and then check for time and then schedule
                if current_date == start_date:
                    # main(['', kwargs_path])
                    print(f"Meeting: "
                          f"{meeting.get('id', '') if meeting.get('id', '') else meeting.get('tag', 'SBP100')} "
                          f"is scheduled today!")
                    os.system(f'python3 {script_path} {kwargs_path} >{logs_path} 2>&1')
                else:
                    print(f"Sorry! Meeting: "
                          f"{meeting.get('id', '') if meeting.get('id', '') else meeting.get('tag', 'SBP100')} "
                          f"isn't scheduled today!")
                    os.system(f'rm -rf {meeting_dir}')


if __name__ == '__main__':
    script()

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
