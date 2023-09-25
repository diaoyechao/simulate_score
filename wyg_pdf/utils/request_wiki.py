# -- coding: utf-8 --
"""
#@Author : 田杰
#@Email : 491666889@qq.com
#@Software : PyCharm
#@Time : 2023/8/17 17:29
"""
import re
import json

import requests

from configs.model_config import WIKI_URL


def get_wiki_token():
    S = requests.Session()
    CSRF_TOKEN = ""
    try:
        PARAMS_1 = {
            "action": "query",
            "meta": "tokens",
            "type": "login",
            "format": "json"
        }

        R = S.get(url=WIKI_URL, params=PARAMS_1)
        DATA = R.json()
        LOGIN_TOKEN = DATA['query']['tokens']['logintoken']

        PARAMS_2 = {
            "action": "clientlogin",
            "username": "Auto update",
            "password": "tianjie491",
            "loginreturnurl": "http://172.27.115.210:8888/",
            "format": "json",
            "logintoken": LOGIN_TOKEN
        }

        R = S.post(WIKI_URL, data=PARAMS_2)

        PARAMS_3 = {
            "action": "query",
            "meta": "tokens",
            "format": "json",
            "type": "csrf"
        }

        R = S.get(url=WIKI_URL, params=PARAMS_3)
        DATA = R.json()

        CSRF_TOKEN = DATA['query']['tokens']['csrftoken']
    except:
        pass
    return CSRF_TOKEN, S


def get_project_id(project_name):
    """
    通过名称获取ID
    """
    project_id = None
    try:
        params = {
            "action": "wbsearchentities",
            "search": project_name,
            "limit": 1,
            "format": "json",
            "language": "zh-cn"
        }
        response = requests.get(WIKI_URL, params=params)
        if response.status_code == 200:
            data = response.json()
            if data["search"][0]["label"] == project_name:
                project_id = data["search"][0]["id"]
    except:
        project_id = None
    return project_id


def get_property_id(project_name):
    """
    通过名称获取ID
    """
    project_id = None
    try:
        params = {
            "action": "wbsearchentities",
            "search": project_name,
            "limit": 1,
            "type": "property",
            "format": "json",
            "language": "zh-cn"
        }
        response = requests.get(WIKI_URL, params=params)
        if response.status_code == 200:
            data = response.json()
            if data["search"][0]["label"] == project_name and data["search"][0]["datatype"] == 'monolingualtext':
                project_id = data["search"][0]["id"]
    except:
        project_id = None
    return project_id


def set_property_id(title):
    """
    创建属性，并设置为单语文本
    """
    data = None
    token, S = get_wiki_token()
    try:
        creat_item_data = json.dumps({
            "labels": {
                "zh-cn": {
                    "language": "zh-cn",
                    "value": title
                }
            },
            "datatype": "monolingualtext"
        }, ensure_ascii=False)
        params = {
            "action": "wbeditentity",
            "new": "property",
            "token": token,
            "data": creat_item_data,
            "format": "json",
            "formatversion": "2"
        }
        response = S.post(WIKI_URL, data=params)
        if response.status_code == 200:
            data = response.json()["entity"]["id"]
    except:
        data = None
    return data


def get_title_id(titles: list) -> dict:
    """
    获取title的ID，如果没有ID，创建一个ID
    """
    title_ids_dict = {}
    for title in titles:
        title_id = get_property_id(title)
        if title_id is None:
            title_id = set_property_id(title)
        title_ids_dict[title] = title_id
    return title_ids_dict


def cut(obj, sec):
    return [obj[i:i+sec] for i in range(0,len(obj),sec)]


def split_content(content, sentence_len=390) -> list:
    contents = [i for i in content.split("\n") if i]
    contents_split = []  # 将\n分段后仍然过长的文本进行切分
    for content in contents:
        if len(content) >= sentence_len:
            ele1 = re.sub(r'([;|；|!|。|！])', r'\1\n', content)
            ele1_ls = ele1.split("\n")
            for ele_ele1 in ele1_ls:
                if len(ele_ele1) > sentence_len:
                    ele_ele2 = cut(ele_ele1, sentence_len)
                    contents_split.extend(ele_ele2)
                else:
                    contents_split.append(ele_ele1)
        else:
            contents_split.append(content)
    return [re.sub(r"\t", "  ", i.strip()) for i in contents_split if re.sub(r"\t", "  ", i.strip())]


def update_to_wiki(title, docs):
    """
    将解析好的pdf内容上传到wiki
    title: 规范标题
    docs: [{"title": 章节标题, “content”: 章节内容}]
    """
    docs = [{"title": i["title"] if i["title"] else "*",
             "content": i["content"]}
            for i in docs]
    doc_title = list(set([i["title"] for i in docs]))
    doc_title_ids = get_title_id(doc_title)
    data = None
    try:
        title_dict = {"labels": {"zh-cn": {"language": "zh-cn", "value": title}}}
        claims = []
        for doc in docs:
            doc_contents = split_content(doc["content"])
            for doc_content in doc_contents:
                claims.append({
                    "mainsnak": {
                        "snaktype": "value",
                        "property": doc_title_ids.get(doc["title"], None),
                        "datavalue": {
                            "value": {
                                "text": doc_content,
                                "language": "zh-cn"
                            },
                            "type": "monolingualtext"
                        },
                        "datatype": "monolingualtext"
                    },
                    "type": "statement",
                    "rank": "normal"
                })
        title_dict.update({"claims": claims})
        creat_item_data = json.dumps(title_dict, ensure_ascii=False)
        token, S = get_wiki_token()
        params = {
            "action": "wbeditentity",
            "new": "item",
            "token": token,
            "data": creat_item_data,
            "format": "json",
            "formatversion": "2"
        }
        response = S.post(WIKI_URL, data=params)
        if response.status_code == 200:
            data = response.json()
            if data['success'] == 1:
                return "上传成功，ID：{}".format(data["entity"]["id"])
    except Exception as e:
        return "上传失败，报错信息：{} \ndata: {}".format(str(e), json.dumps(data, ensure_ascii=False))
    return "上传失败，报错信息：{}".format(json.dumps(data, ensure_ascii=False))



if __name__ == '__main__':
    update_res = update_to_wiki("标题：测试（田杰）",
                                [{"title": "章节标题1", "content": "章节内容1"},
                                 {"title": "章节标题2", "content": "章节内容2"}])
    print(update_res)
