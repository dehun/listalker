import mechanize
import cookielib
import re
import time
import logging
import random

config = {
    'linkedin': {
        'login': 'your@email.com',
        'password': 'your_password_here',
        'sleep': 1
    },
    'database': {
        'url': 'sqlite://listalker.sqlite'
    },
    'browser': {
        'user-agent': 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1'
    },
    'victims': {
        'search-requests': [
            'hr+stuttgart',
            'hr+prague'],
        'search-url-pattern': 'http://www.linkedin.com/vsearch/f?type=all&keywords=%(keywords)s&orig=GLHD&rsid=&pageKey=member-home&page_num=%(page)d',
        'to_visit_count': 50
    }
}


def create_browser():
    browser = mechanize.Browser()
    # configure browser
    cookies = cookielib.LWPCookieJar()
    browser.set_cookiejar(cookies)

    browser.set_handle_robots(False)
    browser.set_handle_gzip(True)
    browser.set_handle_equiv(True)
    browser.set_handle_referer(True)
    browser.set_handle_redirect(True)
    browser.addheaders = [('User-agent',
                           config['browser']['user-agent'])]
    return browser


def linkedin_login(browser):
    logging.info("logging in into linkedin")
    browser.open('http://www.linkedin.com')
    browser.select_form(nr=0)
    browser.form['session_key'] = config['linkedin']['login']
    browser.form['session_password'] = config['linkedin']['password']
    browser.submit()


def get_victims_from_search_page(page_response):
    """ gather victims from the page"""
    data = page_response.get_data()
    for profile_search in re.finditer('"link_nprofile_view_.+?":"(.+?)"',
                                      data):
        yield 'http://www.linkedin.com' + profile_search.groups()[0]


def get_victim_from_search_request(browser, search_request):
    logging.info("searching by request %s", search_request)
    for page_number in range(0, 10):
        logging.info("going through page %s", page_number)
        r = browser.open(config['victims']['search-url-pattern']
                         % {'keywords': search_request,
                            'page': page_number})
        time.sleep(config['linkedin']['sleep'])
        for v in get_victims_from_search_page(r):
            yield v


def victims_via_requests(browser, requests):
    for search_request in requests:
        for v in get_victim_from_search_request(browser, search_request):
            yield v


def extract_id_from_victim(victim):
    return re.search('\?id=(.+?)&', victim).groups()[0]


def hunt_for_victims():
    browser = create_browser()
    # open the top link
    logging.info("opening top page www.linkedin.com")
    browser.open('http://www.linkedin.com')
    # login into
    linkedin_login(browser)
    # get victims
    victims = set(victims_via_requests(browser,
                                       config['victims']['search-requests']))

    # uniquify victims by id
    seen = set()
    victims = [seen.add(extract_id_from_victim(v)) or v
               for v in victims
               if extract_id_from_victim(v) not in seen]

    # limit victims to number from config
    random.shuffle(victims)
    victims = victims[0:config['victims']['to_visit_count']]

    # visit victims
    logging.info("going to visit %d persons", len(victims))
    for victim in victims:
        logging.info("visiting %s via url %s",
                     extract_id_from_victim(victim), victim)
        browser.open(victim)
        browser.back()
        time.sleep(config['linkedin']['sleep'])


if __name__ == '__main__':
    logging.basicConfig(format="[%(asctime)s][%(levelname)s] %(message)s",
                        level=logging.INFO)

    hunt_for_victims()
