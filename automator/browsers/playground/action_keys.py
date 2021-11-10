import os
import time
# import webdriver
from selenium import webdriver
  
# import Action chains 
from selenium.webdriver.common.action_chains import ActionChains
  
# import KEYS
from selenium.webdriver.common.keys import Keys

chromedriver_path = os.getenv("LOCAL_CHROMEDRIVER_PATH")
geckodriver_path = os.getenv("GECKO_PATH")


# create webdriver object
driver = webdriver.Firefox(executable_path=geckodriver_path)
#driver = webdriver.Chrome(chromedriver_path)
  
# get geeksforgeeks.org
driver.get("https://www.geeksforgeeks.org/")
  
time.sleep(3)
# create action chain object
action = ActionChains(driver)

# Only some actions are allowed (and they are getting less in each browser version?)
# Currently, the only one working from below is Ctrl+a
# See https://sqa.stackexchange.com/a/12753
# Or https://github.com/SeleniumHQ/selenium/issues/7793
# Or https://github.com/mozilla/geckodriver/issues/1075
# perform the operation

ActionChains(driver).key_down(Keys.CONTROL).send_keys("f").perform()
ActionChains(driver).key_down(Keys.CONTROL).send_keys("a").perform()
ActionChains(driver).key_down(Keys.CONTROL).send_keys("t").perform()
ActionChains(driver).key_down(Keys.CONTROL).send_keys("j").perform()
ActionChains(driver).key_down(Keys.CONTROL).send_keys("b").perform()

# Solution that currently works in firefox only: https://stackoverflow.com/a/59111830/11782367 
# Works with selenium 3 and 4, but only in firefox, so I cannot use it
driver.set_context("chrome")

ActionChains(driver).key_down(Keys.CONTROL).send_keys("f").perform()
ActionChains(driver).key_down(Keys.CONTROL).send_keys("a").perform()
ActionChains(driver).key_down(Keys.CONTROL).send_keys("t").perform()
ActionChains(driver).key_down(Keys.CONTROL).send_keys("j").perform()
ActionChains(driver).key_down(Keys.CONTROL).send_keys("b").perform()

driver.set_context("content")