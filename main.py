#!/usr/bin/env python
# coding=utf-8

# 下一步需要实现语音端点检测（End-Point Detection，EPD）的目标是决定信号的语音开始和结束的位置（又可称为Speech Detection或Voice Activity Detection（VAD））

import pyaudio
from pyaudio import PyAudio, paInt16
import numpy as np
from datetime import datetime
import wave
import time
import urllib, urllib2, pycurl
import base64
import json
import os
from array import array
import sys
reload(sys)
sys.setdefaultencoding("utf-8")

baidu_app_cuid = 9240067

# NUM_SAMPLES = 2000      # pyAudio内部缓存的块的大小
SAMPLING_RATE = 8000    # 取样频率（百度支持8000和16000，测试下来16000效果比较差）
CHANNELS = 1            # 声道数，百度stt仅支持单声道，请填写 1
REC_FORMAT = paInt16    # 16bit 量化
LEVEL = 1500            # 声音保存的阈值
COUNT_NUM = 22          # NUM_SAMPLES个取样之内出现COUNT_NUM个大于LEVEL的取样则记录声音
SAVE_LENGTH = 8         # 声音记录的最小长度：SAVE_LENGTH * NUM_SAMPLES 个取样
CHUNK = SAMPLING_RATE*2 # pyaudio 内部缓存块大小
REC_SECONDS = 3         # 记录时常
LONG_TIME = int(SAMPLING_RATE / CHUNK * REC_SECONDS) # if time is beyond 3 ,force stop

THRESHOLD = 200  # Adjust this to be slightly above the noise level of your recordings.
nquit = 40 # number of silent frames before terminating the program

silent = 0
nover = 0
keepgoing = True
spxlist=[]  # list of the encoded speex packets/frames

save_count = 0
save_buffer = []
t = 0
sum = 0
time_flag = 0
flag_num = 0
#filename = "voice.wav"
duihua = "1"

RECOGNIZE_FLG = True

def get_token():
    # 填写apikey以及secretkey获得token
    apiKey = "FGlra89tCUsox47DPMnuGeHo"
    secretKey = "2732bd5d8674262219dae57ad19454aa"

    auth_url = "https://openapi.baidu.com/oauth/2.0/token?grant_type=client_credentials&client_id=" + apiKey + \
               "&client_secret=" + secretKey;
    res = urllib2.urlopen(auth_url)
    json_data = res.read()
    return json.loads(json_data)['access_token']


def dump_res(buf):
    global duihua
    global RECOGNIZE_FLG
    # print "字符串类型"
    print (buf)
    a = eval(buf)
    # print("#############################")
    # print type(a)

    # 语言解析出来以后，做一些判断检测
    if a['err_msg']=='success.':
        #print a['re sult'][0]#终于搞定了，在这里可以输出，返回的语句
        duihua = a['result'][0]
        if len(duihua) > 10:
            print("对话是真 ### %s, 长度 %s" % (duihua, len(duihua)))
            RECOGNIZE_FLG = True
        else:
            print("对话是假 XXX %s, 长度 %s" % (duihua, len(duihua)))
            RECOGNIZE_FLG = False
    else:
        RECOGNIZE_FLG = False
        print ("recognize failure,don't send to AI roboot")


def use_cloud(token):
    fp = wave.open(filename, 'rb')
    nf = fp.getnframes()
    f_len = nf * 2
    audio_data = fp.readframes(nf)
    cuid = "9240067"
    srv_url = 'http://vop.baidu.com/server_api' + '?cuid=' + cuid + '&token=' + token
    http_header = [
        'Content-Type: audio/pcm; rate=8000',
        'Content-Length: %d' % f_len
    ]

    c = pycurl.Curl()
    c.setopt(pycurl.URL, str(srv_url))  # curl doesn't support unicode
    # c.setopt(c.RETURNTRANSFER, 1)
    c.setopt(c.HTTPHEADER, http_header)  # must be list, not dict
    c.setopt(c.POST, 1)
    c.setopt(c.CONNECTTIMEOUT, 30)
    c.setopt(c.TIMEOUT, 30)
    c.setopt(c.WRITEFUNCTION, dump_res)
    c.setopt(c.POSTFIELDS, audio_data)
    c.setopt(c.POSTFIELDSIZE, f_len)
    c.perform()  # pycurl.perform() has no return val


# 将data中的数据保存到名为filename的WAV文件中
def save_wave_file(filename, data):
    wf = wave.open(filename, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(SAMPLING_RATE)
    wf.writeframes("".join(data))
    wf.close()


# 静音检测
def silent_check(record_data):
    return max(array('h', record_data)) < 5000

# 打开声音设备
pa = PyAudio()
stream = pa.open(format=REC_FORMAT, channels=CHANNELS, rate=SAMPLING_RATE, input=True,
                 frames_per_buffer=CHUNK)
print("the PyAudio version is %s:" % pyaudio.get_portaudio_version())
print("\n")

print("the default input device info:")
print(pa.get_default_input_device_info())
print("\n")

print("the default output device info:")
print(pa.get_default_output_device_info())
print("\n")
stream.stop_stream()

# def voice_recoder()
#     os.system('arecord -D "plughw:1,0" -f S16_LE -d 3 -r 8000 ./0.wav')
#     print('record done...')

#获取百度 token
token = get_token()
print("hi Min the baidu token is %s ", token)

# 图灵机器人配置
key = '056258f84bdc41a099a5f507b31db77e'
api = 'http://www.tuling123.com/openapi/api?key=' + key + '&info='

# 得到图灵机器人的反馈
def getHtml(url):
    page = urllib.urlopen(url)
    html = page.read()
    return html


#基本处理流程
# 接收语音并存储语音文件 --->
# 将语音文件送往百度stt--->
# stt 数据送往图灵机器人--->
# 得到图灵机器人反馈--->
# 反馈文字送往百度tts--->
# tts数据送往语音设备（mpg123）播放--->

# 记录时长
counter = SAMPLING_RATE/(CHUNK * REC_SECONDS)

while True:

    # 打开声音设备（USB microphone）
    # stream = pa.open(format=REC_FORMAT, channels=CHANNELS, rate=SAMPLING_RATE, input=True,
    #                  frames_per_buffer=NUM_SAMPLES)

    # 开启声音输入
    stream.start_stream()

    while True:

        # 静音检测
        # 读入NUM_SAMPLES个取样
        string_audio_data = stream.read(num_frames=CHUNK)

        # 将读入的数据转换为数组
        audio_data = np.fromstring(string_audio_data, dtype=np.short)
        print("audio_data = %s" % audio_data)

        # 计算大于LEVEL的取样的个数
        larger_sample_count = np.sum(audio_data > LEVEL)
        print("the beyond the level sample count is %s" % larger_sample_count)
        temp = np.max(audio_data)
        print("the max sample value is %s" % temp)

        if temp > 5000 and larger_sample_count > COUNT_NUM:

            save_buffer.append(string_audio_data)
            print("声音存储到buffer， 声音长度 %s" % len(save_buffer))

            # 将save_buffer中的数据写入WAV文件，WAV文件的文件名是保存的时刻
            if len(save_buffer) > 0:
                #filename = datetime.now().strftime("%Y-%m-%d_%H_%M_%S") + ".wav"
                filename = str(flag_num)+".wav"
                flag_num += 1
                if flag_num > 30:
                    flag_num = 0

                save_wave_file(filename, save_buffer)
                save_buffer = []

                print filename, "保存成功正在进行语音识别"

                result = use_cloud(token)
                print filename, "语音识别完成"

                # 如果语音解析成功就送往baidu，如果不成功直接返回
                if RECOGNIZE_FLG is False:
                    # 停止录音，重新开始
                    stream.stop_stream()
                    # 清空Buffer
                    save_buffer = []
                    # 直接返回
                    break

                info = duihua
                duihua = ""
                request = api + info
                response = getHtml(request)
                dic_json = json.loads(response)

                # print '机器人: '.decode('utf-8') + dic_json['text']
                # huida = ' '.decode('utf-8') + dic_json['text']
                a = dic_json['text']
                print type(a)
                unicodestring = a

                # 将Unicode转化为普通Python字符串："encode"
                utf8string = unicodestring.encode("utf-8")

                print type(utf8string)
                print str(a)


                #数据送往百度tts
                url = "http://tsn.baidu.com/text2audio?tex=" + dic_json['text'] + \
                      "&lan=zh&per=0&pit=1&spd=7&cuid=%s&ctp=1&tok=%s" % (baidu_app_cuid, token)

                #播放声音
                os.system('mpg123 "%s"' % (url))

                # 关闭录音
                stream.stop_stream()
                print("close the stream ")
                break
            else:
                # 清空buffer
                save_buffer = []


