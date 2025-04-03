import random

import requests, json, time
import os
import base64

from google.cloud import texttospeech_v1

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'INSERT YOUR GOOGLE TTS APPLICATION CREDENTIALS HERE'

#updating question count read
GITHUB_TOKEN = 'INSERT GITHUB TOKEN'
REPO_OWNER = 'YOUR USER'
REPO_NAME = 'REPO NAME'
FILE_PATH = 'QUESTION COUNT FILE'
COMMIT_MESSAGE = 'Update message count'
INITIAL_MESSAGE_COUNT = 0


headers = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3+json',
}

def get_file_sha(file_path):
    url = f'https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{file_path}'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        file_info = response.json()
        return file_info['sha']
    elif response.status_code == 404:
        return None  # File does not exist yet
    else:
        raise Exception(f'Error fetching file SHA: {response.json()}')


def get_message_count():
    url = f'https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        file_info = response.json()
        content = base64.b64decode(file_info['content']).decode('utf-8')
        return int(content.strip())
    elif response.status_code == 404:
        return INITIAL_MESSAGE_COUNT  # File does not exist yet
    else:
        raise Exception(f'Error fetching message count: {response.json()}')


def update_message_count(count):
    url = f'https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}'

    # Get the current file SHA if it exists
    file_sha = get_file_sha(FILE_PATH)

    # Encode the content to Base64
    encoded_content = base64.b64encode(str(count).encode('utf-8')).decode('utf-8')

    # Prepare the data for the API request
    data = {
        'message': COMMIT_MESSAGE,
        'content': encoded_content,
    }
    if file_sha:
        data['sha'] = file_sha

    # Make the API request to update the file
    response = requests.put(url, headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        print('Message count updated successfully.')
    else:
        raise Exception(f'Error updating message count: {response.json()}')








def get_audio(question):
    num = random.randint(0, 10000)
    client = texttospeech_v1.TextToSpeechClient()
    text = question

    synthesis_input = texttospeech_v1.SynthesisInput(text=text)

    voice = texttospeech_v1.VoiceSelectionParams(
        language_code='en-US',
        name='en-US-Wavenet-J',
        ssml_gender=texttospeech_v1.SsmlVoiceGender.MALE
    )

    audio_config = texttospeech_v1.AudioConfig(
        audio_encoding=texttospeech_v1.AudioEncoding.MP3
    )

    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config
    )
    with open('output' + str(num) + '.mp3', 'wb') as f:
        f.write(response.audio_content)
        f.close()

    return 'output' + str(num) + '.mp3'

def get_question(catList, diffList):
    message_count = get_message_count()

    message_count += 1
    update_message_count(message_count)
    url = "https://www.qbreader.org/api" + "/random-tossup"

    subs = {
        "American Literature": "Literature",
        "British Literature": "Literature",
        "Classical Literature": "Literature",
        "European": "Literature",
        "World Literature": "Literature",
        "Other Literature": "Literature",
        "American History": "History",
        "Ancient History": "History",
        "European History": "History",
        "World History": "History",
        "Other History": "History",
        "Biology": "Science",
        'Chemistry': "Science",
        "Physics": "Science",
        "Other Science": "Science",
        "Visual Fine Arts": "Fine Arts",
        "Auditory Fine Arts": "Fine Arts",
        "Other Fine Arts": "Fine Arts"
    }

    altSubs = {
        "Drama": "Other Literature",
        "Long Fiction": "Other Literature",
        "Poetry": "Other Literature",
        "Short Fiction": "Other Literature",
        "Misc Literature": "Other Literature",
        "Math": "Other Science",
        "Astronomy": "Other Science",
        "Computer Science": "Other Science",
        "Earth Science": "Other Science",
        "Engineering": "Other Science",
        "Misc Science": "Other Science",
        "Architecture": "Other Fine Arts",
        "Dance": "Other Fine Arts",
        "Film": "Other Fine Arts",
        "Jazz": "Other Fine Arts",
        "Opera": "Other Fine Arts",
        "Photography": "Other Fine Arts",
        "Misc Arts": "Other Fine Arts",
        "Anthropology": "Social Science",
        "Economics": "Social Science",
        "Linguistics": "Social Science",
        "Psychology": "Social Science",
        "Sociology": "Social Science",
        "Other Social Science": "Social Science"

    }
    newCatList = catList.copy()
    subcats = []
    altSubCats = []
    for i in newCatList:
        if i in subs.keys():
            subcats.append(i)
            newCatList.remove(i)
    for i in newCatList:
        if i in subs.keys():
            subcats.append(i)
            newCatList.remove(i)

    for i in subcats:
        for key, value in subs.items():
            if i == key and value not in newCatList:
                newCatList.append(value)

    for i in newCatList:
        if i in altSubs.keys():
            altSubCats.append(i)
            newCatList.remove(i)
    for i in newCatList:
        if i in altSubs.keys():
            altSubCats.append(i)
            newCatList.remove(i)

    for i in altSubCats:
        for key, value in altSubs.items():
            if i == key and value not in subcats:
                subcats.append(value)

    res = [eval(i) for i in diffList]
    data = {
        "alternateSubcategories": altSubCats,
        "categories": newCatList,
        "subcategories": subcats,
        "difficulties": res,
        "number": 1,
        "minYear": 2014
    }

    response = requests.get(url, params=data)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(str(response.status_code) + " bad request")








def get_bonus(catList, diffList):
    message_count = get_message_count()

    message_count += 3
    update_message_count(message_count)
    url = "https://www.qbreader.org/api" + "/random-bonus"

    subs = {
        "American Literature": "Literature",
        "British Literature": "Literature",
        "Classical Literature": "Literature",
        "European": "Literature",
        "World Literature": "Literature",
        "Other Literature": "Literature",
        "American History": "History",
        "Ancient History": "History",
        "European History": "History",
        "World History": "History",
        "Other History": "History",
        "Biology": "Science",
        'Chemistry': "Science",
        "Physics": "Science",
        "Other Science": "Science",
        "Visual Fine Arts": "Fine Arts",
        "Auditory Fine Arts": "Fine Arts",
        "Other Fine Arts": "Fine Arts"
    }

    altSubs = {
        "Drama": "Other Literature",
        "Long Fiction": "Other Literature",
        "Poetry": "Other Literature",
        "Short Fiction": "Other Literature",
        "Misc Literature": "Other Literature",
        "Math": "Other Science",
        "Astronomy": "Other Science",
        "Computer Science": "Other Science",
        "Earth Science": "Other Science",
        "Engineering": "Other Science",
        "Misc Science": "Other Science",
        "Architecture": "Other Fine Arts",
        "Dance": "Other Fine Arts",
        "Film": "Other Fine Arts",
        "Jazz": "Other Fine Arts",
        "Opera": "Other Fine Arts",
        "Photography": "Other Fine Arts",
        "Misc Arts": "Other Fine Arts",
        "Anthropology": "Social Science",
        "Economics": "Social Science",
        "Linguistics": "Social Science",
        "Psychology": "Social Science",
        "Sociology": "Social Science",
        "Other Social Science": "Social Science"

    }
    newCatList = catList.copy()
    subcats = []
    altSubCats = []
    for i in newCatList:
        if i in subs.keys():
            subcats.append(i)
            newCatList.remove(i)
    for i in newCatList:
        if i in subs.keys():
            subcats.append(i)
            newCatList.remove(i)

    for i in subcats:
        for key, value in subs.items():
            if i == key and value not in newCatList:
                newCatList.append(value)

    for i in newCatList:
        if i in altSubs.keys():
            altSubCats.append(i)
            newCatList.remove(i)
    for i in newCatList:
        if i in altSubs.keys():
            altSubCats.append(i)
            newCatList.remove(i)

    for i in altSubCats:
        for key, value in altSubs.items():
            if i == key and value not in subcats:
                subcats.append(value)

    res = [eval(i) for i in diffList]
    data = {
        "alternateSubcategories": altSubCats,
        "categories": newCatList,
        "subcategories": subcats,
        "difficulties": res,
        "number": 1,
        "minYear": 2014
    }

    response = requests.get(url, params=data)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(str(response.status_code) + " bad request")


def check(question, answer):
    return confirm(question, answer)


def confirm(answerline, givenanswer):
    url = "https://www.qbreader.org/api/check-answer"
    data = {
        "answerline": answerline,
        "givenAnswer": givenanswer
    }

    response = requests.get(url, params=data)
    return response.json()
