import json

import re

# 标题层级
title_level = open("config/title.txt", encoding="utf-8").readlines()

enterprise_award_dict = json.load(open("config/enterprise_awards.json", encoding="utf-8"))


def get_enterprise_award(text):
    result = {}
    for first_key, first_values in enterprise_award_dict.items():
        first_result = []
        for second_key, second_values in first_values.items():
            for alias in second_values:
                if re.search(alias, text):
                    result[first_key] = first_result.append(second_key)
                    break
        result[first_key] = first_result
    return result


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
