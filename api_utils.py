import requests


def download_file(save_dir, url):
    """
    下载云文件并存储到本地
    :param save_dir: 云文件下载本地存放目录
    :param url: 云文件地址
    :return: 下载文件存放目录
    """
    req = requests.get(url, verify=False)
    file_name = url.split('/')[-1]
    file_path = save_dir + file_name
    with open(file_path, 'wb') as f:
        f.write(req.content)
    return file_path
