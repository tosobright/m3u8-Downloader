# -*- coding:utf-8 -*-
import os
import sys
import requests
import datetime
from Crypto.Cipher import AES
from binascii import b2a_hex, a2b_hex
import threadpool
import time
import socket


def GetPlayLists(url):
    flist = []
    key = ''

    all_content = requests.get(url).text

    if "#EXTM3U" not in all_content:
        print u"Not m3u8" + all_content.decode('GBK')

    if "EXT-X-STREAM-INF" in all_content:  # 第一层
        file_line = all_content.split("\n")
        for line in file_line:
            if '.m3u8' in line:
                url = url.rsplit("/", 1)[0] + "/" + line  # 拼出第二层m3u8的URL
                all_content = requests.get(url).text
                file_line = all_content.split("\n")

                for item in file_line:
                    if "#" not in item:
                        if item != "":
                            flist.append(url.rsplit("/", 1)[0] + "/" + item)
                    else:
                        if "#EXT-X-KEY" in item:  # 找解密Key
                            method_pos = item.find("METHOD")
                            comma_pos = item.find(",")
                            method = item[method_pos:comma_pos].split('=')[1]
                            print u"Decode Method：", method

                            uri_pos = item.find("URI")
                            quotation_mark_pos = line.rfind('"')
                            key_path = item[uri_pos:quotation_mark_pos].split('"')[
                                1]

                            key_url = url.rsplit(
                                "/", 1)[0] + "/" + key_path  # 拼出key解密密钥URL
                            res = requests.get(key_url)
                            key = res.content
                            print u"key：", key

    return flist, key


def mergefile(downloadpath, filepath):
    path = os.path.dirname(downloadpath)
    os.chdir(path)
    cmd = "copy /b *.mp4 " + '"' + filepath + '"'
    print cmd.decode('GBK')
    os.system(cmd)


def download(filepath, playlists, key):
    length = len(playlists)
    if len(key):  # AES 解密
        cryptor = AES.new(key, AES.MODE_CBC, key)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.146 Safari/537.36"}

    # 增加断点续传
    logfilename = os.path.split(filepath)[1].split('.')[0] + '.lf'
    logfile = os.path.split(filepath)[0] + '\\' + logfilename
    if os.path.exists(logfile):
        with open(logfile, 'r') as f:
            DownLoadedIndex = int(f.read())
    else:
        DownLoadedIndex = -1

    for index, url in enumerate(playlists):
        # 是否下载判定
        if index > DownLoadedIndex:
            notOK = True
            while notOK:
                try:
                    res = requests.get(url, timeout=5, headers=headers)
                    #print res.content
                    # s.decode('GBK')
                    if res.status_code == 200:
                        print (os.path.split(filepath)[
                            1] + " : " + str(index)+"|"+str(length-1) + "   ").decode('GBK')
                        if len(key):  # AES 解密
                            with open(filepath, 'ab') as f:
                                f.write(cryptor.decrypt(res.content))
                        else:
                            with open(filepath, 'ab') as f:
                                f.write(res.content)
                        time.sleep(1)
                        notOK = False
                        with open(logfile, 'w') as f:
                            f.write(str(index))

                except Exception as e:
                    print (os.path.split(filepath)[
                        1] + '  retry...' + str(e)).decode('GBK')
                    time.sleep(5)


def multidownload(filepath, url, process):
    playlists, key = GetPlayLists(url)
    if len(playlists) != 0:
        print 'Total Length:', len(playlists)

        if len(playlists) <= process:
            process = len(playlists)

        splitlength = len(playlists)/process + 1
        splitlist = [playlists[i:i+splitlength]
                     for i in range(0, len(playlists), splitlength)]
        print splitlength, len(splitlist)
        param = []
        for index, lists in enumerate(splitlist):
            fp = filepath.rsplit("\\", 1)[
                0] + "\\" + str(index).zfill(3)+filepath.rsplit("\\", 1)[1]
            dict = {'filepath': fp, 'playlists': lists, 'key': key}
            param.append((None, dict))

        pool = threadpool.ThreadPool(process)
        requests = threadpool.makeRequests(download, param)
        [pool.putRequest(req) for req in requests]
        pool.wait()
        pool.dismissWorkers(process)

        return True
    else:
        return False


def InitDownDir(dir):
    if os.path.exists(dir):
        for root, dirs, files in os.walk(dir):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
    else:
        os.mkdir(dir)


def M3u8Down(filepath, url, process):
    #filepath = "G:\\m3u8\\1.mp4"
    downloadpath = filepath.rsplit(
        "\\", 1)[0] + "\\download\\"+filepath.rsplit("\\", 1)[1]
    downloaddir = filepath.rsplit("\\", 1)[0] + "\\download"
    finish = downloaddir + "\\Finish.end"
    if os.path.exists(finish):
        InitDownDir(downloaddir)

    if multidownload(downloadpath, url, process):
        print 'merge______________'
        mergefile(downloadpath, filepath)
        with open(finish, 'w') as f:
            f.write(url)


def UpdateDownLists(path):
    with open(path, "r+") as f:
        fl = f.readlines()
        fl.pop(0)
        f.seek(0)
        f.truncate()  # 清空文件
        f.writelines(fl)


if __name__ == '__main__':
    socket.setdefaulttimeout(20)
    # DnsDef(['223.5.5.5','223.6.6.6'])
    downfilepath = 'C:\Users\Administrator\Desktop\m3u8\downlist.txt'
    m3u8DownDir = "F:\\m3u8\\"

    with open(downfilepath, 'r') as f:
        fl = f.read()
    m3u8list = fl.split('\n')
    for item in m3u8list:
        if item != '':
            #print item
            filename, url = item.split('$')[0], item.split('$')[1]
            #print filename,url
            filepath = m3u8DownDir + filename + ".mp4"
            M3u8Down(filepath, url, 50)
            UpdateDownLists(downfilepath)
            time.sleep(10)
    print u'Download completion...'
