import markovify
from selenium import webdriver
import random
import time
from tweetcache import TweetCache
import re
from cloudvision import VisionApi


class Markov:
    def build_tweet(self):
        # print('Building tweet....')
        text_model = markovify.Text(self.text)

        tweet = text_model.make_short_sentence(140)
        while len(tweet) < 70:
            tweet = text_model.make_short_sentence(140)
        return tweet

    def __init__(self, raw_text):
        print('trying to initialize text with all tweets.')
        self.text = raw_text


class Bot:
    def __init__(self):
        self.browser = webdriver.Firefox()
        self.trending_dictionary = {}
        self.trending_elements_names = []
        self.tweets = []
        self.formatted_tweets = []
        self.image_urls = []

    def navigate(self, url):
        self.browser.get(url)

    @staticmethod
    def sleep_range(min, max):
        time.sleep(random.uniform(min, max))

    @staticmethod
    def click_on_element(element_to_click):
        element_to_click.click()

    def slow_send_keys(self, field, text):
        for c in text:
            field.send_keys(c)
            self.sleep_range(0.03, 0.35)

    def login(self, username, password):
        # Navigate to the login page
        self.navigate('https://twitter.com/login')
        # Sleep for random amount of time
        self.sleep_range(1, 3)
        # Click the username field
        username_field = self.browser.find_element_by_class_name('js-username-field')
        self.slow_send_keys(username_field, username)
        self.sleep_range(1, 3)
        # Click the password field
        password_field = self.browser.find_element_by_class_name('js-password-field')
        self.slow_send_keys(password_field, password)
        self.sleep_range(1, 3)
        # Click the Log in button
        login_button = self.browser.find_element_by_class_name('submit.EdgeButton.EdgeButton--primary.EdgeButtom--medium')
        login_button.click()
        print('Done')

    def send_tweet(self, tweet_to_send):
        # Navigate to twitter home page
        self.navigate('https://twitter.com/')
        self.browser.implicitly_wait(5)
        # Select the field to make it expand
        tweet_field = self.browser.find_element_by_id('tweet-box-home-timeline')
        tweet_field.click()
        self.browser.implicitly_wait(5)
        # select the field to type into it
        tweet_field = self.browser.find_element_by_id('tweet-box-home-timeline')
        # tweet_field.click()
        self.sleep_range(3, 5)
        self.slow_send_keys(tweet_field, tweet_to_send)
        tweet_field.click()
        self.sleep_range(3, 5)
        # Click the tweet button
        tweet_button = self.browser.find_element_by_class_name('tweet-action.EdgeButton.EdgeButton--primary.js-tweet-btn')
        tweet_button.click()

    def select_trending_topics(self):
        # Clear the trending list
        self.trending_dictionary = {}
        # Implicitly wait for trending side bar
        self.browser.implicitly_wait(5)
        # Navigate to twitter home page
        self.navigate('https://twitter.com/')
        # Select trending hashtags parent
        trending_elements = self.browser.find_elements_by_class_name('pretty-link.js-nav.js-tooltip.u-linkComplex')
        self.trending_elements_names = self.browser.find_elements_by_class_name('u-linkComplex-target.trend-name')
        for x in range(len(trending_elements)):
            self.trending_dictionary[self.trending_elements_names[x]] = trending_elements[x]

        # For now go ahead and click on the first option
        self.browser.implicitly_wait(10)

    @staticmethod
    def current_time_millis():
        return int(round(time.time() * 1000))

    def scrape_tweets_on_page(self, time_to_scroll):
        milli_start = self.current_time_millis()
        milli_current = self.current_time_millis()
        while milli_current - milli_start < time_to_scroll:
            self.browser.execute_script('window.scrollTo(0, document.body.scrollHeight);')
            self.sleep_range(1, 3)
            milli_current = self.current_time_millis()

        # Scrape Tweets
        regex = re.compile(r'[\n\r\t]');
        self.tweets = self.browser.find_elements_by_class_name('TweetTextSize.js-tweet-text.tweet-text')
        # Remove \n, \r, and \t from the tweets.
        for i in range(len(self.tweets)):
            self.formatted_tweets.append(regex.sub('', self.tweets[i].text))

        # Scrape Image Urls
        image_elements = self.browser.find_elements_by_class_name('AdaptiveMedia-photoContainer.js-adaptive-photo')
        for image in image_elements:
            self.image_urls.append(image.get_attribute('data-image-url'))

        print('Num Tweets: ' + str(len(self.tweets)))
        print('Num Images: ' + str(len(self.image_urls)))


def main():
    cache = TweetCache()

    #vision = VisionApi()

    bot = Bot()
    bot.login('TrendySimulator', '7mDZJ7PEfbdie77')
    bot.sleep_range(1, 3)
    bot.select_trending_topics()

    # Get list of current trends and ask the user which one they want to use
    print("Current trends on twitter:")
    for i, name in enumerate(bot.trending_elements_names):
        print("  %d. %s" % (i + 1, name.text))

    selected_trend_index = int(input("Select a trend [1 thru %d]: " % (len(bot.trending_elements_names)))) - 1
    selected_trend = bot.trending_elements_names[selected_trend_index]
    selected_trend_text = selected_trend.text

    # Load in new tweets if the cache misses
    if cache.cache_age(selected_trend_text) > 5*60*60:  # 5 hours
        bot.trending_dictionary[selected_trend].click()
        bot.sleep_range(3, 7)

        bot.scrape_tweets_on_page(60*1000)

        cache.add_tweets(bot.formatted_tweets, selected_trend_text)
        cache.add_images(bot.image_urls, selected_trend_text)

    # Grab tweets from cache and prep for markov ingestion
    all_text = ''
    tweet_count = 0
    for tweet in cache.get_tweets(selected_trend_text):
        tweet_count += 1
        if not tweet.endswith('.'):
            all_text = all_text + tweet + '. '
        else:
            all_text = all_text + tweet + ' '
    print("Loaded %d tweets" % tweet_count)

    # Generate new tweets
    while True:
        tweet_generator = Markov(all_text)
        suggested_tweets = [tweet_generator.build_tweet() for _ in range(5)]
        print("Suggested tweets:")
        for i, tweet in enumerate(suggested_tweets):
            print("  %d. %s" % (i + 1, tweet))

        choice = int(input("Select a tweet to publish [1 thru %d] or 0 to regenerate: " % len(suggested_tweets)))
        if choice > 0:
            bot.send_tweet(suggested_tweets[choice - 1])
            break


if __name__ == '__main__':
    main()
