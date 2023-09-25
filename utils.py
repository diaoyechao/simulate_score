import json
import re

# 规则识别pattern
fixed_score_rule_patterns = json.load(open("config/fixed_score_rule_patterns.json", encoding="utf-8"))

# 标题层级
title_level = open("config/title.txt", encoding="utf-8").readlines()


def get_rating_sub_items_filter_patterns():
    """
    读取评分子项二次过滤pattern
    :return: 评分子项二次过滤pattern
    """
    rating_sub_items_filter_patterns = ""
    # 评分子项二次过滤pattern
    pattern_file = open("config/filter.txt", encoding="utf-8")
    for pattern in pattern_file.readlines():
        pattern = pattern.strip()
        rating_sub_items_filter_patterns += pattern
    pattern_file.close()
    return rating_sub_items_filter_patterns


def get_rating_sub_items_patterns():
    """
    读取评分子项识别pattern
    :return: 评分子项识别pattern
    """
    rating_sub_items_patterns = ""
    # 评分子项识别pattern
    pattern_file = open("config/pattern.txt", encoding="utf-8")
    for pattern in pattern_file.readlines():
        pattern = pattern.strip()
        rating_sub_items_patterns += pattern
    pattern_file.close()
    return rating_sub_items_patterns


def recognize_rule(sub_item):
    """
    判断评分子项对应的规则
    :param sub_item: 评分子项
    :return: 如果有对应规则，则返回评分子项对应的规则，否则返回None。
    """
    special_pattern = "满足|合理|可行|可靠|酌情赋分|最多得|优|良|得当"
    if len(re.findall("获得", sub_item)) >= 2 or (
            len(re.findall("得\\d+分", sub_item)) >= 2 and not re.search(special_pattern, sub_item)) \
            or (len(re.findall("得\\d+分", sub_item)) >= 2 and len(re.findall("最多得\\d+分", sub_item))) >= 2:
        return "rule3", "满足【】条件得X分，满足【】条件得Y分，满足【】条件得Z分，..."
    for rule, patterns in fixed_score_rule_patterns.items():
        for pattern in patterns:
            if re.match(pattern, sub_item):
                rule, rule_content = rule.split("-")
                return rule, rule_content
    return None


def split_items(item):
    if re.search("方式[一二三四五六七八九十]：", item):
        items = re.split("方式[一二三四五六七八九十]：", item)
    else:
        items = re.split("\\d+、|[一二三四五六七八九十]、|（\\d+）|[一二三四五六七八九十]标段业绩要求：|[\u2460\u2461\u2462\u2463\u2465]", item)
    if len(items) >= 2:
        return items
    return False


def get_chapter_start_end_position(pdf):
    start = 0
    end = 0
    chinese_characters_num_map = {"二": 2, "三": 3, "四": 4}
    num_chinese_characters_map = {value: key for key, value in chinese_characters_num_map.items()}
    start_pattern = "第.*章.*评标办法"
    end_pattern = ""
    for page_index in range(len(pdf.pages)):
        if page_index > 90:
            break
        if page_index < 5:
            continue
        page = pdf.pages[page_index]
        page_content = page.extract_text()
        page_content = "".join(
            ["".join(item.split()) for item in page_content.split("\n") if not re.search("非涉密|项目编号", item)])
        start_match = re.search(start_pattern, page_content[:50])
        if not end_pattern and start_match:
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
            if re.search(end_pattern, "".join(page_content[:50].split())):
                end = page.page_number
                break
    if start == 0:
        raise Exception("没有找到评标办法章节起始索引")
    if end == 0:
        raise Exception("没有找到评标办法章节终止索引")
    if start >= end:
        raise Exception("评标办法章节起始索引大于等于终止索引")
    return start, end


def get_rating_sub_items(start, end, pdf):
    """
    提取出每一页的所有表格中的评分子项内容，添加到评分子项列表中
    :param start:评标办法章节起始位置
    :param end:评标办法章节终止位置
    :param pdf:pdf
    :return: 返回评分子项列表
    """
    rating_sub_items_patterns = get_rating_sub_items_patterns()
    rating_sub_items = []
    last_page_table_row = ""  # 被分割的上一页的表格行内容
    last_page_table_row_bak = ""  # 被分割的上一页的表格行内容
    label = False
    for j in range(start, end + 1):
        page = pdf.pages[j - 1]
        tables = page.extract_tables()
        # tables:每一页所有表格 [[[],[],...,[]],...,[[],[],...,[]]]
        # print(tables)
        # print("------")
        # 提取每一页每一个表格的评分子项内容
        for table in tables:
            # table:每一页每一个表格 [[],[],...,[]]
            # print(table)
            # print("******")
            sign = False
            if re.search("评分分|分值", str(table[0][-1])) and len(str(table[0][-1])) < 5:
                sign = True
            if len([item for item in table[0] if re.search("评审项|条款号|评分因素|评审内容", str(item))]) > 1:
                table = table[1:]
            for index, table_row in enumerate(table):
                # table_row:每一个表格的每一行
                # print(table_row)
                # 处理表格中最后一列为评分分值的情况
                if sign:
                    table_row = table_row[:-1]
                if not table_row[-1]:
                    exist_rating_sub_item = ["".join(str(item).split()) for item in table_row if
                                             re.search(rating_sub_items_patterns, "".join(str(item).split()))]
                    if exist_rating_sub_item:
                        rating_sub_items.extend(exist_rating_sub_item)
                    continue
                # **********************
                for content in table_row[:-1]:
                    result = re.search(rating_sub_items_patterns, str(content))
                    if result:
                        table_row_content_bak = "".join(["".join(content.split()) for content in table_row])
                        for row in table[index + 1:len(table)]:
                            if None in row[:-1]:
                                table_row_content_bak += "".join(
                                    ["".join(content.split()) for content in row if content is not None])
                        last_page_table_row_bak = table_row_content_bak
                        label = True
                if label is True:
                    if (None in table_row[:-1]) or ('' in table_row[:-1]):
                        last_page_table_row_bak += "".join([content for content in table_row if content is not None])
                        rating_sub_items.append("".join(last_page_table_row_bak.split()))
                # **********************
                # 同一表格在不同页上被分割开的内容整合
                # todo 还需优化
                if index == 0:
                    if (None in table_row[:-1]) or ('' in table_row[:-1]):
                        last_page_table_row += "".join(table_row[-1].split())
                        # print(last_page_table_row)
                        search_rating_item = re.search(rating_sub_items_patterns, last_page_table_row)
                        # 判断是否存在评分子项，如果存在，则添加到评分子项列表中。
                        if search_rating_item:
                            rating_sub_items.append(last_page_table_row)
                        last_page_table_row = ""
                        continue
                # 直接取每一个表格行的最后一个单元格的内容
                table_row_content = "".join(table_row[-1].split())
                search_rating_item = re.search(rating_sub_items_patterns, table_row_content)
                # print(table_row_content)
                # print("%%%%%%")
                # 判断是否存在评分子项，如果存在，则添加到评分子项列表中。
                if search_rating_item:
                    if not recognize_rule(table_row_content) or re.search("有效期", table_row_content):
                        rating_sub_items.append(
                            "，".join(["".join(item.split()) for item in table_row if item and not item.isdigit()]))
                    else:
                        rating_sub_items.append(table_row_content)
                if index == len(table) - 1:
                    last_page_table_row = "".join(table_row[-1].split())
    # print("")
    # for rating_sub_item in rating_sub_items:
    #     print(rating_sub_item)
    #     print("******")
    # exit()

    # 对小单元格继续进行拆分
    split_rating_sub_items = []
    for sub_item in rating_sub_items:
        count = 0
        items = split_items(sub_item)
        if items:
            for item in items:
                if re.search(rating_sub_items_patterns, item):
                    count += 1
                    if count > 1:
                        break
            if count > 1:
                for item in items:
                    if re.search(rating_sub_items_patterns, item):
                        split_rating_sub_items.append(item)
            else:
                split_rating_sub_items.append(sub_item)
        else:
            split_rating_sub_items.append(sub_item)

    # 去重 去除多余信息：example：（注：...）
    filtered_split_rating_sub_items = []
    for index, item in enumerate(split_rating_sub_items):
        unuseful_mes_start_index = item.find("备注：") if item.find("备注：") != -1 else item.find("注：")
        if index == len(split_rating_sub_items) - 1:
            if unuseful_mes_start_index != -1:
                filtered_split_rating_sub_items.append(item[:unuseful_mes_start_index])
            else:
                filtered_split_rating_sub_items.append(item)
            break
        if item in split_rating_sub_items[index + 1]:
            continue
        else:
            if unuseful_mes_start_index != -1:
                filtered_split_rating_sub_items.append(item[:unuseful_mes_start_index])
            else:
                filtered_split_rating_sub_items.append(item)
    return list(dict.fromkeys(filtered_split_rating_sub_items))


def is_integer_or_float(input_str):
    try:
        int_value = int(input_str)  # 尝试将字符串转换为整数
        return int_value  # 如果成功，返回True和整数值
    except ValueError:
        try:
            float_value = float(input_str)  # 尝试将字符串转换为浮点数
            return float_value  # 如果成功，返回True和浮点数值
        except ValueError:
            return False, None  # 如果都失败，返回False


def judge_evaluation_method_pdf(start, end, pdf):
    """
    从评标办法章节起始页到终止页中提取评估方法
    :param start: 起始页
    :param end: 终止页
    :param pdf:
    """
    for j in range(start, end + 1):
        page = pdf.pages[j - 1]
        page_content = "".join(page.extract_text().split())
        if re.search("综合评估法|综合评分法", page_content):
            return re.search("综合评估法|综合评分法", page_content).group()
    return None


def judge_evaluation_method_word(doc):
    paragraphs = doc.paragraphs
    for paragraph in paragraphs:
        paragraph_text = "".join(paragraph.text.split())
        if re.search("综合评估法|综合评分法", paragraph_text):
            return re.search("综合评估法|综合评分法", paragraph_text).group()
    return None


def get_bid_rejection_rule_pdf(pdf):
    bid_rejection_rule = ""
    is_table = False
    for page_index in range(len(pdf.pages)):
        page = pdf.pages[page_index]
        tables = page.extract_tables()
        for table in tables:
            for table_row in table:
                for item in table_row:
                    if item and re.search("废标", item):
                        bid_rejection_rule = "，".join(["".join(item.split()) for item in table_row if item])
                        is_table = True
                        break
        if not is_table:
            page_content = page.extract_text()
            if "废标" in page_content:
                bid_rejection_rule_page_content = "".join(page_content.split())
                # example0:[一二三四五六七八九十]、@\d+、@（\d+）
                levels = ['[一二三四五六七八九十]、', '\\d+、']
                result = []
                level0_splits = re.split(levels[0], bid_rejection_rule_page_content)
                for level0_split in level0_splits:
                    level1_split = re.split(levels[1], level0_split)
                    result.extend(level1_split)
                if len(result) != 1:
                    start_index = 0
                    for index, item in enumerate(result):
                        if "废标" in item:
                            start_index = index
                    start_item = result[start_index]
                    end_index = start_index + 1
                    if end_index > len(result) - 1:
                        end_item = result[end_index]
                        bid_rejection_rule = bid_rejection_rule_page_content[bid_rejection_rule_page_content.find(
                            start_item):bid_rejection_rule_page_content.find(end_item)]
                    else:
                        bid_rejection_rule = bid_rejection_rule_page_content[
                                             bid_rejection_rule_page_content.find(start_item):]
                    if bid_rejection_rule:
                        return bid_rejection_rule
                # example1:\\d+.\\d+.\\d+
                level_1 = "\\d+.\\d+.\\d+"
                result = re.split(level_1, bid_rejection_rule_page_content)
                if len(result) != 1:
                    bid_rejection_rule = "".join([item for item in result if re.search("废标", item)])
                    if bid_rejection_rule:
                        return bid_rejection_rule
    if is_table and not re.search("废标条款", bid_rejection_rule):
        split_items = re.split(r"\d、|\b\d{2}\b、", bid_rejection_rule)
        bid_rejection_rule = "".join([item for item in split_items if re.search("废标", item)])
    return bid_rejection_rule


def get_bid_rejection_rule_word(doc):
    bid_rejection_rules = []
    paragraphs = doc.paragraphs
    all_content = ""
    for paragraph in paragraphs:
        paragraph_text = "".join(paragraph.text.split())
        all_content += paragraph_text
    all_contents = re.split("[一二三四五六七八]、|\\d+、|（\\d+）", all_content)
    for content in all_contents:
        if content and "废标" in content:
            bid_rejection_rules.append(content)
    return bid_rejection_rules
