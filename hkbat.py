#!/usr/bin/python2
# from hkreloaded import updatedb; updatedb.updatedb()
from __future__ import print_function
from __future__ import division

from sys import path
import re
import csv
import os

from lxml import html
import requests

#### SETTINGS ####
queryHK = True
hkApi = True
priceLists = 1
hkLevel = 1 # 0 is standard, 1 is gold, 2 is platinum
numPages = 0 # 0 is all
csvName = 'batteries'
##################

fieldnames = ['id', 'url', 'name', 'cap', 'ser', 'wh', 'price', 'pwh', 'stock', 'whouse']

warehouses = ['XX', 'US', 'AR', 'AU', 'GB', 'BR']

batteries = [] 

def loadCsv(batteries, csvPath):
    with open(csvPath) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            batteries.append(row)
    print('Read from csv file.')
    
def saveCsv(batteries, csvPath):
    with open(csvPath, 'w') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in batteries:
            writer.writerow(row)

if priceLists:
    csvName += '-tuples.csv'
else:
    csvName += '.csv'
csvPath = os.path.realpath(os.path.join(path[0], csvName))
print(csvPath)

if queryHK:
    batteries = [] 
    print('Scraping HK website')
else:
    try:
        loadCsv(batteries, csvPath)
    except FileNotFoundError:
        queryHK = 1
    if len(batteries) == 0:
        queryHK = 1

if queryHK:
    for whouse in warehouses:
        print('Warehouse: '+whouse)
        pageNo=1
        while 1:
            url = 'http://www.hobbyking.com/hobbyking/store/uh_listCategoriesAndProducts.asp?cwhl='+whouse+'&idCategory=86&v=&sortlist=P&CatSortOrder=asc&curPage='+str(pageNo)
            page = requests.get(url)
            tree = html.fromstring(page.text)
            names = tree.xpath('//a[@style="text-decoration:none; font-size:12px"]/text()')
            names = [t.strip() for t in names]
            urls = tree.xpath('//a[@style="text-decoration:none; font-size:12px"]/@href')
            pids = [url.split('__')[1] for url in urls]
            if len(pids) != len(names):
                print("Links and Names Don't Match!")
                break
            for i in range(0,len(names)):
                batteries.append({'id':pids[i], 'name':names[i], 'url':'http://www.hobbyking.com/hobbyking/store/'+urls[i], 'whouse':whouse})
            pageNo += 1
            print(len(batteries))
            if len(names) < 50:
                break
            if numPages != 0 and pageNo > numPages:
                break

for bat in batteries:
    cap = re.search(r'(?i)([0-9]+)mAh(,|\s|\Z|$)', bat['name'])
    if cap:
        bat['cap'] = int(cap.group(1))
    else:
        cap = re.search(r'(?i)([0-9]+)Ah(,|\s|\Z|$)', bat['name'])
        if cap:
            bat['cap'] = int(cap.group(1))*1000
        else:
            bat['cap'] = 0

    ser = re.search(r'(?i)(\A|^|\s)([0-9]+)S([0-9]+P)*(,|\s|\Z|$)', bat['name'])
    if ser:
        bat['ser'] = int(ser.group(2))
    else:
        if re.search(r'(?i)([(one)(single)][ -_]*cell)|(3.7V)', bat['name']) is not None:
            bat['ser'] = 1
        else:
            bat['ser'] = 0

    bat['wh'] = bat['ser'] * bat['cap'] * 0.0037 

removedBatteries = [bat for bat in batteries if bat['cap']==0 or bat['ser']==0]

for x in removedBatteries:
    batteries.remove(x)
    print(x)

#print(batteries)
saveCsv(batteries, csvPath)

if hkApi:
    for i in range(0,len(batteries)):
        stock = requests.get('http://www.hobbyking.com/hobbyking_api.asp?id='+str(batteries[i]['id'])+'&switch=1').text
        try:
            batteries[i]['stock'] = int(re.search(r'^\s*(-*[0-9]+)\s*$', stock, re.MULTILINE).group(1))
        except AttributeError:
            print(stock)
        if priceLists:
            batteries[i]['price'] = [.0,.0,.0]
            batteries[i]['pwh'] = [.0,.0,.0]
            for level in range(0,3):
                price = requests.get('http://www.hobbyking.com/hobbyking_api.asp?id='+str(batteries[i]['id'])+'&switch=3&level='+str(level+1)).text
                batteries[i]['price'][level] = float(re.search(r'^\s*([0-9]+\.[0-9]+)\s*$', price, re.MULTILINE).group(1))
                batteries[i]['pwh'][level] = batteries[i]['price'][level]/batteries[i]['wh']
        else:
            price = requests.get('http://www.hobbyking.com/hobbyking_api.asp?id='+str(batteries[i]['id'])+'&switch=3&level='+str(hkLevel+1)).text
            batteries[i]['price'] = float(re.search(r'^\s*([0-9]+\.[0-9]+)\s*$', price, re.MULTILINE).group(1))
            batteries[i]['pwh'] = batteries[i]['price']/batteries[i]['wh']
        print(str(i)+' '+str(batteries[i]['stock'])+' '+str(batteries[i]['price']))

#print(batteries)
print(len(batteries))

saveCsv(batteries, csvPath)
