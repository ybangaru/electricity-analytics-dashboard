import os
import pandas as pd
import datetime
import time
import boto3
from boto3.dynamodb.conditions import Key

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
import shutil

currentdir = os.path.dirname(__file__)
download_path = '/home/ubuntu/electricity-analytics-dashboard/data/iex/'
chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument("start-maximized")
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_experimental_option("prefs", {                                                                                       
"download.default_directory": f"{download_path}",
"download.prompt_for_download": False,
"download.directory_upgrade": True,
"safebrowsing.enabled": True
})


def get_highest_index(table):
    response = table.scan(AttributesToGet=['index'])
    data = response['Items']

    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'], AttributesToGet=['index'])
        data.extend(response['Items'])

    highest_index = max(pd.DataFrame(data)['index'])
    return highest_index

def get_latest_date(table, highest_index):
    query_is = table.query(KeyConditionExpression=Key('index').eq(highest_index))
    latest_date = pd.DataFrame(query_is['Items'])['datetime'].values[0]
    latest_date = datetime.datetime.strptime(latest_date, "%Y-%m-%d %H:%M:%S")
    return latest_date

def get_latest_data(latest_date):
    def waitUntilDownloadCompleted(maxTime=1200):
        driver.execute_script("window.open()")
        driver.switch_to.window(driver.window_handles[-1])
        driver.get('chrome://downloads')
        endTime = time.time() + maxTime
        while True:
            try:
                downloadPercentage = driver.execute_script(
                    "return document.querySelector('downloads-manager').shadowRoot.querySelector('#downloadsList downloads-item').shadowRoot.querySelector('#progress').value")
                if downloadPercentage == 100:
                    return downloadPercentage
            except:
                pass
            time.sleep(1)
            if time.time() > endTime:
                break

    day_of_month = latest_date.day
    month_of_year = latest_date.strftime("%b")
    year = latest_date.year

    driver = webdriver.Chrome(executable_path="/home/ubuntu/electricity-analytics-dashboard/chrome_driver/chromedriver", options=chrome_options)
    driver.maximize_window()
    driver.implicitly_wait(20)
    driver.get("https://www.iexindia.com/marketdata/areavolume.aspx")

    select = Select(driver.find_element_by_name('ctl00$InnerContent$ddlInterval'))
    select.select_by_visible_text('Hourly')    

    select = Select(driver.find_element_by_name('ctl00$InnerContent$ddlPeriod'))
    select.select_by_visible_text('-Select Range-')

    driver.find_element_by_xpath("//input[@name='ctl00$InnerContent$calFromDate$txt_Date']").click()
    select = Select(driver.find_element_by_xpath("//td[@class='scwHead']/select[@id='scwYears']"))
    select.select_by_visible_text(str(year))
    select = Select(driver.find_element_by_xpath("//td[@class='scwHead']/select[@id='scwMonths']"))
    select.select_by_visible_text(month_of_year)

    driver.find_element_by_xpath(f"//td[@class='scwCells' and text()='{day_of_month}'] | //td[@class='scwCellsWeekend' and text()='{day_of_month}'] | //td[@class='scwInputDate' and text()='{day_of_month}']").click()

    driver.switch_to.default_content()
    driver.find_element_by_xpath("//input[@name='ctl00$InnerContent$calToDate$txt_Date']").click()
    select = Select(driver.find_element_by_xpath("//td[@class='scwHead']/select[@id='scwYears']"))
    select.select_by_visible_text(str(year))
    select = Select(driver.find_element_by_xpath("//td[@class='scwHead']/select[@id='scwMonths']"))
    select.select_by_visible_text(month_of_year)
    driver.find_element_by_xpath(f"//td[@class='scwCells' and text()='{day_of_month}'] | //td[@class='scwCellsWeekend' and text()='{day_of_month}'] | //td[@class='scwInputDate' and text()='{day_of_month}']").click()            
    time.sleep(3)
    driver.find_element_by_xpath("//input[@name='ctl00$InnerContent$btnUpdateReport']").click()
    time.sleep(3)
    driver.find_element_by_xpath("//a[@title='Export drop down menu']").click()
    time.sleep(3)
    driver.find_element_by_xpath("//a[@title='Excel']").click()
    waitUntilDownloadCompleted(180)
    
    filename = max([download_path + f for f in os.listdir(download_path)],key=os.path.getctime)
    shutil.move(filename,os.path.join(download_path,f"{day_of_month}{month_of_year}{year}volumes.xlsx"))

    driver.quit()

    return True

def main():
    AWS_S3_CREDS = {
        "aws_access_key_id"    : os.environ['aws_access_key_id'],
        "aws_secret_access_key": os.environ['aws_secret_access_key'],
        "region_name"          : os.environ['region_name_iex_data'],
    }   
    dynamodb = boto3.resource('dynamodb', **AWS_S3_CREDS)
    table = dynamodb.Table('davolumes')

    highest_index = get_highest_index(table)
    latest_date   = get_latest_date(table, highest_index)
    check = get_latest_data(latest_date)
    if check:
        print(f"Volumes downloaded for {latest_date}")
    else:
        print(f"Volumes download for {latest_date} failed!")


if __name__== '__main__':
    main()