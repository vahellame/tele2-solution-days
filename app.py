# -*- coding: utf-8 -*-

import os
import json
import sys
import time
import uuid
import wave
import datetime
from contextlib import closing

import psycopg2
from flask import Flask, request, send_from_directory
from psycopg2.extras import RealDictCursor
from werkzeug.utils import secure_filename
from flask import jsonify

from vosk import Model, KaldiRecognizer, SetLogLevel

from flask_cors import CORS, cross_origin
from pydub import AudioSegment

UPLOAD_FOLDER = '/home/walt/voice-recognition/upload_files/'

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['JSON_AS_ASCII'] = False
cors = CORS(app)
app.config['CORS_HEADERS'] = 'audio/wav'
SetLogLevel(0)
MODEL = Model("model")

POSTGRES_CONNECTION_PARAMS = {
    "dbname": "sber",
    "user": "postgres",
    "password": "21",
    "host": "localhost",
    "port": 5432
}


def recognize_file(filepath):
    wf = wave.open(filepath, "rb")
    #print("press_f")
    #print(wf.getnchannels())
    #print(wf.getsampwidth())
    #print(wf.getcomptype())
    if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
        print("Audio file must be WAV format mono PCM.", file=sys.stderr)
    rec = KaldiRecognizer(MODEL, wf.getframerate())
    recognition = ""
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            recognition = recognition + json.loads(rec.Result())["text"] + " "
        else:
            rec.PartialResult()

    recognition += json.loads(rec.FinalResult())["text"]

    return recognition


def execute_sql(sql_query, connection_params):
    with closing(psycopg2.connect(cursor_factory=RealDictCursor,
                                  dbname=connection_params["dbname"],
                                  user=connection_params["user"],
                                  password=connection_params["password"],
                                  host=connection_params["host"],
                                  port=connection_params["port"],
                                  )) as conn:
        conn.autocommit = True
        with conn.cursor() as cursor:
            cursor.execute(sql_query)
            try:
                records = cursor.fetchall()
                result = []
                for record in records:
                    result.append(dict(record))
                return result
            except psycopg2.ProgrammingError:
                pass


@app.route('/', methods=['GET', 'POST'])
@cross_origin()
def upload_file():
    if request.method == 'POST':
        blob = request.files['file']
        if blob:
            fname = request.files['file'].filename.split(".")[0]
            data = request.files['file'].read()
            filepath = UPLOAD_FOLDER + fname + datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S_%f') + ".wav"

            #s = time.time()
            with open(filepath, "wb") as f:
                f.write(data)
            #print(s - time.time())
            sound = AudioSegment.from_file(filepath)
            sound = sound.set_channels(1)
            sound = sound.set_sample_width(2)
            sound.export(filepath, format="wav")
            #print(s - time.time())

            wf = wave.open(filepath, "rb")
            #print("_________________________")
            #print(wf.getnchannels())
            #print(wf.getsampwidth())
            #print(wf.getcomptype())
            #print("_________________________")

            re = recognize_file(filepath)

            #execute_sql(f"INSERT into records (path, text) \
            #             VALUES ('{filepath}', '{re}')",
            #            POSTGRES_CONNECTION_PARAMS)
            #response = execute_sql(f"SELECT id, text from records \
            #                       WHERE path='{filepath}'", POSTGRES_CONNECTION_PARAMS)[0]
            #response["text"] = re
            #print(response)
            print(re)
            return re
            # return jsonify(response)
            # return redirect(url_for('uploaded_file', filename=filename))
    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form action="" method=post enctype=multipart/form-data>
      <p><input type=file name=file>
         <input type=submit value=Upload>
    </form>
    '''


@app.route('/test', methods=['GET', 'POST'])
def test():
    d = {'id': 24, 'text': 'аниме'}
    return jsonify(d)


@app.route('/stt/<filename>')
def speech_to_text(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/recognition', methods=["POST"])
def do_something():
    data = request.get_json()
    #print(data)
    #print(type(data))
    text = data["text"]
    tts = gTTS(text=text, lang='ru')
    filepath = UPLOAD_FOLDER + uuid.uuid4().hex + ".mp3"
    tts.save(filepath)
    d = {
        "path": filepath
    }
    return jsonify(d)


app.run(host="0.0.0.0", debug=True)
