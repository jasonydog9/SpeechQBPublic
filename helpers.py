import random

import requests, json, time
import os

from google.cloud import texttospeech_v1

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'infra-hulling-388220-c8bbed4a70df.json'
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
    url = "https://www.qbreader.org/api" + "/random-tossup"

    subcats = []
    res = [eval(i) for i in diffList]
    data = {
        "categories": catList,
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
    url = "https://www.qbreader.org/api" + "/random-bonus"
    subcats = []
    res = [eval(i) for i in diffList]
    data = {
        "categories": catList,
        "subcategories": subcats,
        "difficulties": res,
        "number": 1,
        "minYear": 2014
    }

    response  = requests.get(url, params=data)
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
