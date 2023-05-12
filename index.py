import pyaudio
import wave
import audioop

from requests import post, get
import json
import os
import pygame
from urllib import parse
import shutil
import tempfile

THRESHOLD = 20
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

while True:
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK,
                    input_device_index=1)

    frames = []
    silent_frames = 0
    should_record = True

    context = []

    while should_record:
        data = stream.read(CHUNK)
        frames.append(data)

        # Analisar o nível de som dos últimos 10 quadros
        last_n_frames = frames[-10:]
        rms = audioop.rms(b"".join(last_n_frames), 2)
        # Se o nível de som for menor que o limiar, contar mais um quadro de silêncio
        if rms < THRESHOLD:
            silent_frames += 1
        else:
            silent_frames = 0

        # Se houver 10 quadros consecutivos de silêncio, parar de gravar
        if silent_frames > 10:
            should_record = False

    stream.stop_stream()
    stream.close()
    p.terminate()

    with wave.open("output.wav", "wb") as wf:
        print("Estou pensando...")
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b"".join(frames))
        os.system('ffmpeg -i output.wav -f s16le -acodec pcm_s16le output.raw -loglevel quiet -y')
        results = post(
            'https://www.google.com/speech-api/v2/recognize?output=json&lang=pt-BR&key=AIzaSyBOti4mM-6x9WDnZIjIeyEU21OpBXqWBgw&pFilter=0',
            files={'file': open('output.raw', 'rb')}, headers={'Content-type': 'audio/l16; rate=48000'})
        userSpeaked = json.loads(results.text.replace('{"result":[]}', ''))['result'][0]['alternative'][0]['transcript']
        context.append({'content': userSpeaked, 'role': 'user'})
        chatGpt = post('https://api.openai.com/v1/chat/completions',
                       json={'messages': context, 'model': "gpt-3.5-turbo"}, headers={
                'Authorization': 'Bearer <key>',
                'Content-Type': 'application/json'
            })
        chatGpt = json.loads(chatGpt.text)
        os.remove('output.raw')
        voiceEncoded = get("https://translate.google.com/translate_tts?ie=UTF-8&q=" + parse.quote(
            chatGpt['choices'][0]['message'][
                'content']) + "&tl=pt&total=1&idx=0&textlen=" + str(len(chatGpt['choices'][0]['message'][
                'content'])) +"&client=tw-ob&prev=input&ttsspeed=1")
        with open("answer.mp3", 'wb') as f:
            f.write(voiceEncoded.content)
            f.close()
        pygame.mixer.init()
        context.append({'content': chatGpt['choices'][0]['message']['content'], 'role': 'assistant'})
        try:
            pygame.mixer.music.load("answer.mp3")
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            pygame.mixer.music.unload()
        except pygame.error:
            print(chatGpt['choices'][0]['message']['content'])
        temp_dir = tempfile.gettempdir()
        shutil.move("answer.mp3", os.path.join(temp_dir, "answer.mp3"))
        question = input("Deseja fazer outra pergunta? (s/n): ")
        if question == 'n':
            break