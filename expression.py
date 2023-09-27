import re

from utils import get_enterprise_award


def get_expression(sub_item, conditions):
    score_expressions = []
    time_pattern = r"\d{4}年\d{1,2}月\d{1,2}日|\d{4}年\d{1,2}月"
    time = ""
    if re.search(time_pattern, sub_item):
        time = re.search(time_pattern, sub_item).group()
    # 企业奖项
    if re.search("奖", sub_item):
        global_name = get_enterprise_award(sub_item).get("奖项名称", None)
        for score_item in conditions:
            score_expression = {
                "expression": "",
                "calculation_method": "",
            }
            expression = {"奖项等级": "", "奖项分级": "", "奖项名称": "", "时间": time}
            X = re.search(r"得\d+分|得\d+(\.\d+)?分|的\d+|的\d+(\.\d+)?分", score_item).group()
            score = re.search(r"\d+(\.\d+)?|\d+", X).group()
            calculation_method = f"count*{score}"
            score_expression["calculation_method"] = calculation_method
            local_name = get_enterprise_award(score_item).get("奖项名称", None)
            if local_name:
                expression["奖项名称"] = local_name[0]
                for key, value in get_enterprise_award(score_item).items():
                    if value:
                        expression[key] = value[0]
            elif global_name:

                expression["奖项名称"] = global_name[0]
                for key, value in get_enterprise_award(score_item).items():
                    if value:
                        expression[key] = value[0]
            else:
                for key, value in get_enterprise_award(score_item).items():
                    if value:
                        expression[key] = value[0]
            score_expression["expression"] = expression
            score_expressions.append(score_expression)
    return score_expressions
