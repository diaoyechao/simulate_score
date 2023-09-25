import datetime
import os
import re
import subprocess

import docx
import pdfplumber
import requests

from rules import *
from utils import *


def is_pdf(file_path):
    with open(file_path, 'rb') as file:
        header = file.read(4)
    return header == b'%PDF'


def is_word(file_path):
    with open(file_path, 'rb') as file:
        header = file.read(2)
    return header == b'\xd0\xcf'


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


def score_analysis(file_path):
    with pdfplumber.open(file_path) as pdf:
        start, end = get_chapter_start_end_position(pdf)
        print(f"@1.评标办法章节开始位置{start}，结束位置{end}。")
        print("------")
        filtered_split_rating_sub_items = get_rating_sub_items(start, end, pdf)

    print("")
    print("@2.评分子项内容")
    for filtered_split_rating_sub_item in filtered_split_rating_sub_items:
        print(filtered_split_rating_sub_item)
        print("******")

    fixed_score_items = []
    subject_score_items = []
    if os.path.exists("result.txt"):
        os.remove("result.txt")
    w = open("./result.txt", "a", encoding="utf-8")
    for sub_item in filtered_split_rating_sub_items:
        # 可计算得分项
        # 判断评分子项对应的规则
        w.write(sub_item + "\n")
        # print(sub_item)
        rule = recognize_rule(sub_item)
        w.write(str(rule) + "\n")
        w.write("\n")
        # print(rule)
        # print("&&&&&&")
        if rule:
            if rule[0] == "rule1":
                rule1_fixed_score_items = rule1(sub_item)
                if rule1_fixed_score_items["scoreItem"]:
                    fixed_score_items.append(rule1_fixed_score_items)
            if rule[0] == "rule2":
                rule2_fixed_score_items = rule2(sub_item)
                if rule2_fixed_score_items["scoreItem"]:
                    fixed_score_items.append(rule2_fixed_score_items)
            elif rule[0] == "rule3":
                rule3_fixed_score_items = rule3(sub_item)
                if rule3_fixed_score_items["scoreItem"]:
                    fixed_score_items.append(rule3_fixed_score_items)
        else:
            subject_score_items.append(sub_item)

    print("")
    print("@3.可计算得分项内容及其对应规则")
    fixedScoreResp = []
    for fixed_score_item in fixed_score_items:
        fixedScoreResp.append(fixed_score_item)
        print(fixed_score_item)
        print("******")

    print("")
    print("@4.主观得分项及其对应最大分值")
    subjectiveScoreResp = []
    for subject_score_item in subject_score_items:
        if len(subject_score_item) < 30:
            continue
        subject_score_item_dict = {
            "scoreItem": None,
            "maxScore": None,
            "scoreType": 2,
            "defaultScore": None
        }
        max_score_pattern = "最多得\\d+分|最高得(\\d+)分|满分\\d+分|最高不超过(\\d+)分|得\\d+分|得\\d+(\\.\\d+)?分" \
                            "|得\\d+(\\.\\d+)?～\\d+分|得\\d+(\\.\\d+)?～\\d+(\\.\\d+)?分"
        max_score_iter = re.finditer(max_score_pattern, subject_score_item)
        scores = [max_score.group() for item in max_score_iter for max_score in
                  re.finditer("\\d+(\\.\\d+)?|\\d+", item.group())]

        scores = [int(score) if isinstance(is_integer_or_float(score), int) else float(score) for score in scores]
        if scores:
            subject_score_item_dict["maxScore"] = max(scores)
        subjectiveScoreResp.append(subject_score_item_dict)
    print(subjectiveScoreResp)
    businessScoreResp = {
        "businessScoreItem": None,
        "controlPrice": None,
        "upRuleRate": None,
        "downRuleRate": None,
        "basicRate": None,
        "basicPrice": None,
        "scoreType": 3
    }
    # 获取当前时间
    current_time = datetime.datetime.now()
    # 将当前时间转换为时间戳（以秒为单位）
    timestamp = current_time.timestamp()

    final = {
        "success": True,
        "msg": "请求成功。",
        "code": 200,
        "data": {
            "fixedScoreResp": fixedScoreResp,
            "subjectiveScoreResp": subjectiveScoreResp,
            "businessScoreResp": businessScoreResp
        },
        "timestamp": timestamp
    }
    print("")
    print("@5.final response")
    print(final)
    return final


def is_doc_or_docx(file_path):
    return file_path.split(".")[-1]


def doc2docx(doc_path, docx_path):
    cmd = '/bin/libreoffice --headless --convert-to docx'.split() + [doc_path] + ['--outdir'] + [docx_path]
    p = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    p.wait(timeout=30)


def get_bidding_announcement_start_end_position(pdf):
    start = 0
    end = 0
    chinese_characters_num_map = {"一": 1, "二": 2, "三": 3, "四": 4}
    num_chinese_characters_map = {value: key for key, value in chinese_characters_num_map.items()}
    start_pattern = "第.*章.*招标公告"
    end_pattern = ""
    for page_index in range(len(pdf.pages)):
        if page_index > 90:
            break
        page = pdf.pages[page_index]
        page_content = page.extract_text()
        if re.search(r"目录|目\s+录", page_content):
            continue
        start_match = re.search(start_pattern, "".join(page_content[:100].split()))
        if start_match:
            start = page.page_number
            chinese_characters_pattern = r"\第(.+?)\章"
            chinese_characters_start_num = re.search(chinese_characters_pattern, start_match.group()).group(1)
            if chinese_characters_start_num.isdigit():
                end_pattern = f"第{int(chinese_characters_start_num) + 1}章"
            else:
                start_num = chinese_characters_num_map[chinese_characters_start_num]
                end_num = start_num + 1
                chinese_characters_end_num = num_chinese_characters_map[end_num]
                end_pattern = f"第{chinese_characters_end_num}章"
        if end_pattern:
            if re.search(end_pattern, "".join(page_content[:200].split())):
                end = page.page_number
                break
    if start == 0:
        raise Exception("没有找到招标公告章节起始索引")
    if end == 0:
        raise Exception("没有找到招标公告章节终止索引")
    if start > end:
        raise Exception("招标公告章节起始索引大于终止索引")
    return start, end


def get_bidding_announcement_parse_result(bidding_announcement_content, title):
    """
    调用招标公告信息抽取接口获取解析结果
    :param bidding_announcement_content: 招标公告内容
    :param title: 标题
    :return: 解析结果
    """
    response = requests.post(url="http://192.168.60.139:8001/api/tender/tenderInformation",
                             json={"content": bidding_announcement_content,
                                   "title": title})
    response_json = response.json()
    bidding_document_parse_result = {}
    for key, value in response_json["data"].items():
        if key == "5" or key == "6":
            continue
        if value["project_name"] == "行业分类":
            bidding_document_parse_result["industryType"] = value["label_name"]
        if value["project_name"] == "招标类型分类":
            bidding_document_parse_result["projectStage"] = value["label_name"]
        if value["project_name"] == "是否接受联合体投标":
            bidding_document_parse_result["isAccept"] = value["label_name"]
    proxyOrgTelephone = ""
    for json_item in response_json["data"]["5"]:
        if json_item["label_name"] == "项目名称":
            bidding_document_parse_result["projectName"] = json_item["value"]
        if json_item["label_name"] == "建设地点":
            bidding_document_parse_result["projectAddress"] = json_item["value"]
        if json_item["label_name"] == "项目招标编号":
            bidding_document_parse_result["projectNo"] = json_item["value"]
        if json_item["label_name"] == "招标单位联系电话":
            bidding_document_parse_result["projectTelephone"] = json_item["value"]
            bidding_document_parse_result["bidUnitTelephone"] = json_item["value"]
        if json_item["label_name"] == "招标单位":
            bidding_document_parse_result["bidUnit"] = json_item["value"]
        if json_item["label_name"] == "招标文件获取网址":
            bidding_document_parse_result["webSiteUrl"] = json_item["value"]
        if json_item["label_name"] == "招标单位地址":
            bidding_document_parse_result["bidUnitAddress"] = json_item["value"]
        if json_item["label_name"] == "招标代理机构":
            bidding_document_parse_result["proxyOrg"] = json_item["value"]
        if json_item["label_name"] == "招标代理机构地址":
            bidding_document_parse_result["proxyOrgAddress"] = json_item["value"]
        if json_item["label_name"] == "代理机构联系人":
            proxyOrgTelephone += json_item["value"]
        if json_item["label_name"] == "代理联系人电话":
            proxyOrgTelephone += json_item["value"]
        if json_item["label_name"] == "投标企业资质要求":
            bidding_document_parse_result["enterpriseQualification"] = json_item["value"]
        if json_item["label_name"] == "投标企业注册地要求":
            bidding_document_parse_result["enterpriseAddress"] = json_item["value"]
        if json_item["label_name"] == "投标企业备案要求":
            bidding_document_parse_result["enterpriseBackup"] = json_item["value"]
        if json_item["label_name"] == "投标企业财务要求":
            bidding_document_parse_result["enterpriseFinance"] = json_item["value"]
        if json_item["label_name"] == "投标企业业绩要求":
            bidding_document_parse_result["enterpriseKpi"] = json_item["value"]
        if json_item["label_name"] == "项目负责人资质要求":
            bidding_document_parse_result["projectLeaderQualification"] = json_item["value"]
        if json_item["label_name"] == "项目负责人业绩要求":
            bidding_document_parse_result["projectLeaderKpi"] = json_item["value"]
        if json_item["label_name"] == "项目负责人职称要求":
            bidding_document_parse_result["projectLeaderPm"] = json_item["value"]
        if json_item["label_name"] == "招标文件领取开始时间":
            if json_item.get("norm", None):
                bidding_document_parse_result["startTime"] = json_item["norm"]
        if json_item["label_name"] == "招标文件领取结束时间":
            if json_item.get("norm", None):
                bidding_document_parse_result["endTime"] = json_item["norm"]
    bidding_document_parse_result["proxyOrgTelephone"] = proxyOrgTelephone
    return bidding_document_parse_result


def bidding_document_parse(file_path):
    bidding_document_parse_result = {
        "projectName": None,
        "projectNo": None,
        "projectTelephone": None,
        "bidControlPrice": None,  # todo
        "industryType": None,
        "projectStage": None,
        "bidUnit": None,
        "bidUnitAddress": None,
        "bidUnitTelephone": None,
        "proxyOrg": None,
        "proxyOrgAddress": None,
        "proxyOrgTelephone": None,
        "enterpriseQualification": None,
        "enterpriseAddress": None,
        "enterpriseBackup": None,
        "enterpriseFinance": None,
        "enterpriseKpi": None,
        "projectLeaderQualification": None,
        "projectLeaderKpi": None,
        "projectLeaderPm": None,
        "isAccept": None,
        "startTime": None,
        "contractLimit": None,
        "endTime": None,
    }
    if is_pdf(file_path) or os.path.splitext(file_path)[1] == ".pdf":
        with pdfplumber.open(file_path) as pdf:
            start, end = get_chapter_start_end_position(pdf)
            evaluation_method = judge_evaluation_method_pdf(start, end, pdf)
            bid_rejection_rule = get_bid_rejection_rule_pdf(pdf)
            bid_rejection_rules = [item for item in re.split("\\d+、", bid_rejection_rule)][1:]
            start_, end_ = get_bidding_announcement_start_end_position(pdf)
            bidding_announcement_content = ""
            title = pdf.pages[0].extract_text().split("\n")[0]
            for page_index in range(start_, end_):
                page = pdf.pages[page_index - 1]
                tables = page.find_tables()
                if tables:
                    # todo
                    pass
                page_content = page.extract_text()
                bidding_announcement_content += page_content
            bidding_document_parse_result.update(
                get_bidding_announcement_parse_result(bidding_announcement_content, title))
            bidding_document_parse_result["abandoneRuleList"] = bid_rejection_rules
            bidding_document_parse_result["scoreMethod"] = evaluation_method

    if is_word(file_path) or os.path.splitext(file_path)[1] in [".doc", ".docx"]:
        if is_doc_or_docx(file_path) == "doc":
            docx_path = file_path.split(".")[0] + ".docx"
            doc2docx(file_path, docx_path)
        else:
            docx_path = file_path
        doc = docx.Document(docx_path)
        evaluation_method = judge_evaluation_method_word(doc)
        bid_rejection_rule = get_bid_rejection_rule_word(doc)
        paragraphs = doc.paragraphs
        all_contents = "".join(["".join(paragraph.text.split()) for paragraph in paragraphs if paragraph])
        bid_index = all_contents.find("招标公告")
        notice_index = all_contents.find("投标须知")
        bidding_announcement_content = all_contents[bid_index:notice_index]
        title = ""  # todo
        bidding_document_parse_result.update(get_bidding_announcement_parse_result(bidding_announcement_content, title))
        bidding_document_parse_result["abandoneRuleList"] = bid_rejection_rule
        bidding_document_parse_result["scoreMethod"] = evaluation_method
    return bidding_document_parse_result
