#############################################################
# grab.py                                                   #
#                                                           #
# Quick & dirty straightforward Python3 script (no object-  #
# oriented programming so far) to grab questions, answers   #
# and uploaded images from an ask.fm account                #
#                                                           #
#                                                           #
# For website scraping, BeautifulSoup is used. Please make  #
# sure to install BeautifulSoup before running this script. #
#                                                           #
# $ pip install beautifulsoup4                              #
#                                                           #
# You may also need to install requests and lmxl            #
# $ pip install requests                                    #
# $ pip install lxml                                        #
#                                                           #
#   see https://www.crummy.com/software/BeautifulSoup/bs4/doc/#installing-beautiful-soup
#                                                           #
#                                                           #
# This script creates three text files:                     #
#  one for the questions                                    #
#  one for the answers                                      #
#  one for questions and answers together                   #
#                                                           #
# It will also try to download every image hat has been     #
# uploaded to ask.fm as an answer. Videos or linked images  #
# are not supported (yet(?)).                               #
#                                                           #
# All files will be placed in the current directory.        #
#                                                           #
# As said, this is a quick & dirty script that does the job #
# (as of today, of course ask.fm may change their website   #
# structure later so that this script has to be adapted)    #
#                                                           #
# (Almost) no exception or error handling has been          #
# implemented yet, this may be added in later versions.     #
#                                                           #
#############################################################

#############################################################
# Version 1.0 (01-May-2018)
# by LordOfTheSnow
# GitHub: https://github.com/LordOfTheSnow/AskFM-Grabber
#
# published under GNU General Public License v3.0
# see https://choosealicense.com/licenses/gpl-3.0/
#
# Please ensure that you have the right to grab something from a website with this script
# I do not take any legal responsibilities for a misuse of this script
#############################################################


# do some imports
from tqdm import tqdm
import requests
import bs4
import sys
import urllib.request
import datetime
import time
import pickle
# ask.fm pages usually contain all sorts of unicode images that interfer
# with things you might want to do later (i.e. build a wordcloud out of the
# text files), so they are removed here
#
# create translation map for non-bmp charactes
non_bmp_map = dict.fromkeys(range(0x10000, sys.maxunicode + 1), 0xfffd)

def get_all_qa(username,folder=None):
	# change the name of the ask.fm-account you would like to grab
	askURL = 'https://ask.fm' # base URL, do not change
	askURI = '/'+username

	# delay grabbing of next page to prevent potential blocking by ask.fm
	# value is in seconds
	delay = 0.5
	folder='' if folder is None else folder+'/'
	#set up some constants and variables
	filenamePrefix=askURI[1:]
	filenameQandA = filenamePrefix + "_q_and_a.pkl"
	numberOfImagesSaved = 0
	numberOfQuestions = 0
	numberOfAnswers = 0
	numberOfPages = 0

	#open output files
	fileQandA = open (folder+filenameQandA, "wb")
	data=[]
	fileHashs = open ('hashtags.txt','a', encoding='utf-8')
	soup=bs4.BeautifulSoup(requests.get(askURL + askURI).text, 'lxml')
	n_questions = int(soup.find_all("div",class_="profileStats_number profileTabAnswerCount")[0].getText().replace("\xa0",""))

	tqdm_bar=tqdm(total=n_questions,desc=askURI[1:])
	hashtags=[h.text.replace("#","") for h in soup.find_all("div",class_="icon-interest")[0].findAll()]
	for h in hashtags:
		fileHashs.write('{}\n'.format(h))
	fileHashs.close()
	#loop while there still are "next" pages
	while (askURI):
		time.sleep(delay)
		res = requests.get(askURL + askURI)

		soup = bs4.BeautifulSoup(res.text, 'lxml')

		articles = soup.find_all("article")

		for article in articles:
			# get the question
			header = article.header
			h2 = header.h2
			question = h2.get_text("|", strip=True).translate(non_bmp_map)
			tqdm_bar.update(1)
			#print(question)
			# convert to latin-1 to remove all stupid unicode characters
			# you may want to adapt this to your personal needs
			#
			# for some strange reason I have to first transform the string to bytes with latin-1
			# encoding and then do the reverse transform from bytes to string with latin-1 encoding as
			# well... maybe has to be revised later
			# bQuestion = question.encode('latin-1', 'ignore')
			# question = bQuestion.decode('latin-1', 'ignore')
			numberOfQuestions += 1
			
			
			# get the answer
			content=""
			streamItemContent = article.select('.streamItem_content')
			if (len(streamItemContent)):
				if (len(streamItemContent[0].contents) > 1):
					# remove last item of content list as it only contains a 'more...' link
					#del streamItemContent[0].contents[len(streamItemContent[0].contents)-1]
					streamItemContent[0].contents.pop()

					content = str(streamItemContent[0].get_text("|", strip=True)).translate(non_bmp_map)

					# for whatever reasons, sometimes the "View more" text is still there,
					# so remove it here once and forever
					content = content.replace("|View more", "")
					
				if (len(streamItemContent[0].contents) == 1):
					content = str(streamItemContent[0].contents[0]).translate(non_bmp_map)

				# convert to latin-1 to remove all stupid unicode characters
				# you may want to adapt this to your personal needs
				#
				# for some strange reason I have to first transform the string to bytes with latin-1
				# encoding and then do the reverse transform from bytes to string with latin-1 encoding as
				# well... maybe has to be revised later
				content=content.replace('<span dir="rtl">','').replace("</span>",'')
				numberOfAnswers += 1

			#fileQandA.write("{}	{}\n".format(question,content))
			data.append([question,content])


			# maybe there is an image?
			if 0:
				streamItemVisual = article.select('.streamItem_visual')
				if (len(streamItemVisual)):
					link = streamItemVisual[0].find('a')
					visual = link.get('data-url')

					if visual:
						localFilename = (filenamePrefix + "_{0:04d}_".format(numberOfImagesSaved) +
										 visual.split('/')[-1])
						try:
							urllib.request.urlretrieve(visual, localFilename)
							numberOfImagesSaved +=1
						except:
							print("Unexpected error:", sys.exc_info()[0])
					

		# find the link to the next page
		pageNext = soup.select('.item-page-next')

		if (len(pageNext)):
			if 0:
				# only continue if next link is found    
				print ('================================= page ' + str (numberOfPages+1)
					   + " (q: " + str(numberOfQuestions) + ", a: "
					   + str(numberOfAnswers) + ", i: " + str(numberOfImagesSaved) + ")")
			askURI = pageNext[0].get('href')
			numberOfPages +=1
		else:
			askURI = ''

	#uncomment the following line to stop after one page
	#    askURI = ''

	#close all opened files
	pickle.dump(data,fileQandA)

	fileQandA.close()
	tqdm_bar.close()
	#output some results




def get_all_users(hashtags,session,folder=None):
	cookies={'_m_ask_fm_session':session,
			 'locale':'SR'}
	hashtags=','.join(hashtags)
	# change the name of the ask.fm-account you would like to grab
	askURL = 'https://ask.fm' # base URL, do not change
	askURI = '/account/friends/hashtags?q='+hashtags

	# delay grabbing of next page to prevent potential blocking by ask.fm
	# value is in seconds
	delay = 2
	folder='' if folder is None else folder+'/'
	#set up some constants and variables
	filenamePrefix=hashtags
	filenameQandA = filenamePrefix + "_usernames.txt"
	numberOfImagesSaved = 0
	numberOfQuestions = 0
	numberOfAnswers = 0
	numberOfPages = 0

	#open output files
	fileUsers= open (folder+filenameQandA, "w", encoding='utf-8')
	tqdm_bar=tqdm(desc='usernames')
	#loop while there still are "next" pages
	while (askURI):
		time.sleep(delay)
		res = requests.get(askURL + askURI,cookies=cookies)
		soup = bs4.BeautifulSoup(res.text, 'lxml')
		users = soup.find_all("div",class_="item userItem")
		for user in users:

			# get the question
			username=user['data-login']
			fileUsers.write('{}\n'.format(username))
			tqdm_bar.update(1)
			#print(question)
			# convert to latin-1 to remove all stupid unicode characters
			# you may want to adapt this to your personal needs
			#
			# for some strange reason I have to first transform the string to bytes with latin-1
			# encoding and then do the reverse transform from bytes to string with latin-1 encoding as
			# well... maybe has to be revised later
			# bQuestion = question.encode('latin-1', 'ignore')
			# question = bQuestion.decode('latin-1', 'ignore')
					

		# find the link to the next page
		pageNext = soup.select('.item-page-next')

		if (len(pageNext)):
			askURI = pageNext[0].get('href')
			numberOfPages +=1
		else:
			askURI = ''

	#uncomment the following line to stop after one page
	#    askURI = ''

	#close all opened files
	fileUsers.close()
	tqdm_bar.close()
	#output some results

if __name__ == '__main__':
	from os import listdir
	from collections import Counter
	if 0:
		session='MWRRRVliNHE2UGFYSUllWGorNngvTmYzMmNCNi9kTzVLNzBWempZUkIyTHU0eGh2dnNxcGovRXp6SzRKUjVxbzQxbm5GZzlZdWtVbFZjZG1XaHZQZWJrbUppVmdkQm5TNFg4eUJLelpBSU9kaDRCak9YdlNoVi9jM0poQXk0MGZtZWNTWjhWamhhNkhJMEdEY21lWEhFZXJTc3RUaC9WQzN1elBtUmFucFQyRzFFNEI2VXJrZENaMk5FWnRwZERuZHc0bHRDMW9rK0VaVXVzL2cvWlY1RVZ0NnNJOUFzenphREZRRG9uOHViQUpqWUtoVCtLMWRVS0FRMFc0TzhZVi0tRHppc0RiYzdDQXV5N002WXFhbWFPZz09--90be034231b2e26f0d889928b17d998a182d1e03'
		hashtags=['حياة','اسأل','القراءه','سولفوا','سواليف','اللهم_صل_على_سيدنا_محمد♥','شعر_وخواطر','نُجوم',
		'بس','برمجه','سلام']
		with open("hashtags.txt",'r') as fp:
			hashs=fp.read().split("\n")
			old_hashs=[i.replace("_usernames.txt","") for i in listdir("hashtags")]
			hashs=[i for i in hashs if i not in old_hashs]
		hashtags=[i[0] for i in Counter(hashs).most_common(10)]
		for hasthag in tqdm(hashtags,desc='hashtags',ncols=1):
			get_all_users([hasthag],session,folder='hashtags')
	else:
		users=[]
		for filename in listdir("hashtags"):
			for username in open("hashtags/{}".format(filename)):
				users.append(username.replace("\n",''))
		# old_usernames=[i.replace('_q_and_a.pkl','') for i in listdir("users")]
		#username=[i for i in username if i not in old_usernames]
		users=list(set(users))[3143:]
		for username in tqdm(users,desc='users'):
			try:
				get_all_qa(username,folder='users')
			except Exception as e:
				print(str(e))