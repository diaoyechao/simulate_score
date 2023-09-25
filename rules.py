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
    x_pattern = r"得\d+分|得\d+(\.\d+)?分"
    if re.search(x_pattern, sub_item) is not None:
        X = re.search("\\d+", re.search(x_pattern, sub_item).group()).group()
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

    score_expression = {
        "expression": "",
        "calculation_method": "",
        "score_limit": None
    }

    # example:2018年1月1日至今，投标人承担过参与过单项合同总建筑面积不小于7000平方米的建筑设计业绩的，每有1个得7分，本项满分14分。
    x_pattern = r"得\d+分|得\d+(\.\d+)?分"
    if re.search(x_pattern, sub_item) is not None:
        x = re.search(r"\d+(\.\d+)?|\d+", re.search(x_pattern, sub_item).group()).group()
        if isinstance(is_integer_or_float(x), int):
            fixed_score_items["scoreX"] = int(x)
            score_expression["calculation_method"] = f"count*{int(x)}"
        if isinstance(is_integer_or_float(x), float):
            fixed_score_items["scoreX"] = float(x)
            score_expression["calculation_method"] = f"count*{float(x)}"
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
            score_expression["score_limit"] = int(y)
        if isinstance(is_integer_or_float(x), float):
            fixed_score_items["scoreY"] = float(y)
            fixed_score_items["maxScore"] = float(y)
            score_expression["score_limit"] = float(y)
        fixed_score_items["scoreExpression"] = score_expression
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
    split_sub_items = re.split("；", sub_item)
    pattern = "满分\\d+分"
    score_rule = [f"满足【{re.sub(pattern, '', split_sub_item)}】" for split_sub_item in split_sub_items if
                  re.search(r"得\d+分|得\d+(\.\d+)?分|的\d+|的\d+(\.\d+)?分", split_sub_item) and len(split_sub_item) > 10]
    fixed_score_items["scoreRule"] = score_rule
    return fixed_score_items
