from utils import *


def rule1(sub_item):
    """
    规则描述：有则得X分，缺则不得分
    :param sub_item:
    :return:
    """
    fixed_score_items = {"scoreItem": sub_item,
                         "scoreExpression": "",
                         "scoreRule": "",
                         "scoreType": 1,
                         "scoreX": None,
                         "scoreY": None,
                         "maxScore": None,
                         "humanScore": None}
    score_expression = {
        "expression": "",
        "calculation_method": "",
        "score_limit": None
    }
    # example:景观专业负责人具有景观专业中级及以上职称和注册城乡规划师资格的得1分；满分1分；
    if re.search("得\\d+分", sub_item) is not None:
        X = re.search("\\d+", re.search("得\\d+分", sub_item).group()).group()
        rule1 = f"有则得{X}分，缺则不得分"
        fixed_score_items["scoreRule"] = rule1
        score_expression["calculation_method"] = f"count*{int(X)}"
        fixed_score_items["scoreX"] = int(X)
        if re.search("满分\\d+分", sub_item):
            max_score = int(re.search("\\d+", re.search("满分\\d+分", sub_item).group()).group())
            fixed_score_items["maxScore"] = max_score
            score_expression["score_limit"] = max_score
        else:
            max_score = int(X)
            fixed_score_items["maxScore"] = max_score
            score_expression["score_limit"] = max_score
        fixed_score_items["scoreExpression"] = score_expression
    return fixed_score_items


def rule2(sub_item):
    """
    规则描述：每一个得X分，最多得Y分
    :param sub_item:
    :return:
    """
    fixed_score_items = {"scoreItem": sub_item,
                         "scoreExpression": "",
                         "scoreRule": "",
                         "scoreType": 1,
                         "scoreX": None,
                         "scoreY": None,
                         "maxScore": None,
                         "humanScore": None}
    # example:2018年1月1日至今，投标人承担过参与过单项合同总建筑面积不小于7000平方米的建筑设计业绩的，每有1个得7分，本项满分14分。
    x_pattern = r"得\d+分|得\d+(\.\d+)?分"
    if re.search(x_pattern, sub_item) is not None:
        x = re.search(r"\d+(\.\d+)?|\d+", re.search(x_pattern, sub_item).group()).group()
        if isinstance(is_integer_or_float(x), int):
            fixed_score_items["scoreX"] = int(x)
        if isinstance(is_integer_or_float(x), float):
            fixed_score_items["scoreX"] = float(x)
        y_pattern = "最多得\\d+分|最高得(\\d+)分|满分\\d+分|最高不超过(\\d+)分"
        result = re.search(y_pattern, sub_item)
        if result:
            y = re.search("\\d+", result.group()).group()
        else:
            y = x
        fixed_score_items["scoreRule"] = f"每一个得{x}分，最多得{y}分"
        if isinstance(is_integer_or_float(y), int):
            fixed_score_items["scoreY"] = int(y)
            fixed_score_items["maxScore"] = int(y)
        if isinstance(is_integer_or_float(x), float):
            fixed_score_items["scoreY"] = float(y)
            fixed_score_items["maxScore"] = float(y)

    return fixed_score_items


def rule3(sub_item):
    """
    规则描述：满足【】条件得X分，满足【】条件得Y分，满足【】条件得Z分，...
    :param sub_item:
    :return:
    """
    fixed_score_items = {"scoreItem": sub_item,
                         "scoreExpression": "",
                         "scoreRule": "",
                         "scoreType": 1,
                         "scoreX": None,
                         "scoreY": None,
                         "maxScore": None,
                         "humanScore": None}
    # # example:技术负责人具有建筑专业中级及以上职称和一级注册建筑师的得1分，且具有注册城乡规划师的1分；满分2分；
    # if "具有" in sub_item and "且具有" in sub_item:
    #     rule3 = ""
    #     split_sub_items = re.split(r"，|；", sub_item)
    #     for split_sub_item in split_sub_items:
    #         if "具有" in split_sub_item or "且具有" in split_sub_item:
    #             rule3 += f"满足【{split_sub_item}】 "
    #     # fixed_score_items[sub_item] = rule3
    #
    #     final_conditions = []
    #     for _item in split_sub_items:
    #         if "具有" in _item and "且" not in _item:
    #             start = _item.find("具有") + 2
    #             end = re.search("得\\d+分", _item).span()[0]
    #             condition_0 = _item[start:end].replace("的", "")
    #             if "和" in condition_0:
    #                 final_conditions_0 = []
    #                 split_condition_0 = condition_0.split("和")
    #                 for _split in split_condition_0:
    #                     # _split:建筑专业中级及以上职称
    #                     if "及以上" in _split and "中级" in _split:
    #                         first = _split.split("及以上")[0]
    #                         second = first.replace("中级", "") + "高级"
    #                         final_conditions_0.append("(" + first + " or " + second + ")")
    #                     else:
    #                         final_conditions_0.append(_split)
    #                 final_condition_0 = " and ".join(final_conditions_0)
    #                 final_conditions.append(final_condition_0)
    #         if "且" in _item:
    #             start = _item.find("具有") + 2
    #             end = re.search("得\\d+分|的\\d+分", _item).span()[0]
    #             condition_1 = _item[start:end].replace("的", "")
    #             final_conditions.append(condition_1)
    #     # 最后的表达式逻辑拼接
    #     final_conditions_exp = f"({final_conditions[0]}) or (({final_conditions[0]}) and ({final_conditions[1]}))"
    #     # print(final_conditions_exp)
    # # example:景观专业负责人具有景观专业中级及以上职称和注册城乡规划师资格的得1分；满分1分；
    # elif "具有" in sub_item and "且具有" not in sub_item:
    #     split_sub_items = re.split(r"；", sub_item)
    #     for split_sub_item in split_sub_items:
    #         if "具有" in split_sub_item:
    #             rule3 = f"满足【{split_sub_item}】"
    #             # fixed_score_items[sub_item] = rule3
    #     start = sub_item.find("具有") + 2
    #     end = re.search("得\\d+分", sub_item).span()[0]
    #     condition = sub_item[start:end].replace("的", "")
    #     final_conditions = []
    #     if "和" in condition:
    #         split_condition = condition.split("和")
    #         for split in split_condition:
    #             if "及以上" in split and "中级" in split:
    #                 first = split.split("及以上")[0]
    #                 second = first.replace("中级", "") + "高级"
    #                 final_conditions.append("(" + first + " or " + second + ")")
    #             else:
    #                 final_conditions.append(split)
    #     # 最后的表达式逻辑拼接
    #     final_condition_exp = " and ".join(
    #         [f"({final_condition})" if "(" not in final_condition else final_condition for final_condition in
    #          final_conditions])
    #     # print(final_condition_exp)
    # # example:企业承建的项目获得优质工程奖（1分）投标人（或联合体牵头人）承建过的公共建筑工程项目，获得过市级（或以上）优质工程奖的，得1分。
    # elif "获得" in sub_item:
    #     rule3 = f"满足【{sub_item}】"
    #     # fixed_score_items[sub_item] = rule3
    split_sub_items = re.split("；", sub_item)
    pattern = "满分\\d+分"
    score_rule = [f"满足【{re.sub(pattern, '', split_sub_item)}】" for split_sub_item in split_sub_items if
                  re.search(r"得\d+分|得\d+(\.\d+)?分|的\d+|的\d+(\.\d+)?分", split_sub_item) and len(split_sub_item) > 10]
    fixed_score_items["scoreRule"] = score_rule
    return fixed_score_items
