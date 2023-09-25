# -- coding: utf-8 --
"""
#@Author : 田杰
#@Email : 491666889@qq.com
#@Software : PyCharm
#@Time : 2023/8/8 13:57
"""
import re
import copy
import math

import numpy as np


class BoxesConnector(object):
    """
    合并ocr识别的结果，并拼接为文本
    """

    def __init__(self, max_dist_x=3, max_dist_y=3):
        self.max_dist_x = max_dist_x
        self.max_dist_y = max_dist_y

    @staticmethod
    def distance(x1, y1, x2, y2):
        return ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5

    def cal_box_distance(self, box1, box2):
        """
        计算box之间的最小距离与位置关系
        """
        # 首先计算两个矩形中心点
        center1 = box1[0] + box1[2] / 2, box1[1] + box1[3] / 2
        center2 = box2[0] + box2[2] / 2, box2[1] + box2[3] / 2

        # 分别计算两矩形中心点在X轴和Y轴方向的距离
        dist_x = abs(center1[0] - center2[0])
        dist_y = abs(center1[1] - center2[1])

        # 两矩形不相交，在X轴方向有部分重合的两个矩形，最小距离是上矩形的下边线与下矩形的上边线之间的距离
        if dist_x < (box1[2] + box2[2]) / 2 and dist_y >= (box1[3] + box2[3]) / 2:
            return dist_y - (box1[3] + box2[3]) / 2, "y"
        # 两矩形不相交，在Y轴方向有部分重合的两个矩形，最小距离是左矩形的右边线与右矩形的左边线之间的距离
        elif dist_x >= (box1[2] + box2[2]) / 2 and dist_y < (box1[3] + box2[3]) / 2:
            return dist_x - (box1[2] + box2[2]) / 2, "x"
        # 两矩形不相交，在X轴和Y轴方向无重合的两个矩形，最小距离是距离最近的两个顶点之间的距离，
        elif dist_x >= (box1[2] + box2[2]) / 2 and dist_y >= (box1[3] + box2[3]) / 2:
            delta_x = dist_x - (box1[2] + box2[2]) / 2
            delta_y = dist_y - (box1[3] + box2[3]) / 2
            return np.sqrt(np.square(delta_x) + np.square(delta_y)), None
        else:  # 两矩形相交，最小距离为负值，返回-1
            return -1, None

    def merge_box(self, boxes, img_shape):
        """
        合并boxes
        box = [[[253.0, 62.0], [636.0, 65.0], [636.0, 108.0], [253.0, 105.0]], ('中华人民共和国', 0.9013943076133728)]
        """
        # 去除倾斜的box（水印）
        angle = [0 if (i[0][1][0] - i[0][0][0]) == 0 else math.atan((i[0][1][1] - i[0][0][1]) / (i[0][1][0] - i[0][0][0])) * 180 / math.pi for i in boxes]
        boxes = [i for i, j in zip(boxes, angle) if abs(j) < 20]

        # box = [[x, y, w, h], text]
        boxes = [[i[0][0] + [abs(i[0][1][0] - i[0][0][0]), abs(i[0][2][1] - i[0][0][1])], i[1][0]] for i in boxes]

        # 排除全部是英文的box
        boxes = [i for i in boxes
                 if re.match(r"^[a-zA-Z\s]+", i[1]) is None or
                 i[1] != i[1][re.match(r"^[a-zA-Z\s]+", i[1]).start():re.match(r"^[a-zA-Z\s]+", i[1]).end()]]
        # boxes = [i for i in boxes if i[0][3] > 0 and i[0][2] / i[0][3] > 0.5]  # 排除纵横异常的数据

        if boxes:
            percentile_high = np.percentile([i[0][3] for i in boxes], 50)
        else:
            percentile_high = 1
        # avg_high = sum([i[0][3] for i in boxes]) / len([i[0][3] for i in boxes])  # 平均字体高度
        # avg_weight = sum([i[0][2] for i in boxes]) / sum([len(i[1]) for i in boxes])  # 平均字体宽度
        # boxes = [i for i in boxes if i[0][3] < avg_high * 5.0]  # 排除字体异常异常的数据

        merged_x = [[i] for i in range(len(boxes))]
        merged_y = copy.deepcopy(merged_x)
        for x in range(len(boxes)):
            for y in range(x + 1, len(boxes)):
                min_distance, direction = self.cal_box_distance(boxes[x][0], boxes[y][0])
                if direction == "x" and min_distance < self.max_dist_x * percentile_high:
                    merged_x[x].append(y)
                elif direction == "y" and min_distance < self.max_dist_y * percentile_high:
                    merged_y[x].append(y)
        boxes = self.merge_box_x_y(merged_x, merged_y, boxes, img_shape)
        return boxes

    def merge_text(self, boxes):
        """
        将box拼接成文字
        """
        concat_boxes = []
        for box in boxes:
            concat_boxes.extend(box)
        high_95 = np.percentile([i[0][3] for i in concat_boxes if "|" not in i[1]], 95)  # 95分位字体高度
        high_50 = np.percentile([i[0][3] for i in concat_boxes if "|" not in i[1]], 50)  # 50分位字体高度
        width_95 = np.percentile([i[0][2] / len(i[1]) for i in concat_boxes if "|" not in i[1]], 95)  # 95分位字体宽度
        width_50 = np.percentile([i[0][2] / len(i[1]) for i in concat_boxes if "|" not in i[1]], 90)  # 50分位字体宽度
        global_min_x = np.percentile([i[0][0] for i in concat_boxes if "|" not in i[1]], 5)  # 最左侧坐标
        global_max_x = np.percentile([i[0][0] + i[0][2] for i in concat_boxes if "|" not in i[1]], 95)  # 最右侧坐标

        texts = [{"title": "", "content": ""}]

        for page in boxes:
            if len(page) >= 3:
                min_x = np.percentile([i[0][0] for i in page if "|" not in i[1]], 5)  # 最左侧坐标
                max_x = np.percentile([i[0][0] + i[0][2] for i in page if "|" not in i[1]], 95)  # 最右侧坐标
            else:  # 该页信息较少，采用全局高宽
                min_x = global_min_x
                max_x = global_max_x
            for box in page:
                # 该段高度大于95分位且宽度大于95分位，或前后有较大缩进且高度大于50分位，判断为标题
                if box[0][0] > min_x + 3 * width_50 and \
                        box[0][0] + box[0][2] < max_x - 3 * width_50 and \
                        (any([i in box[1][0] for i in [
                            "1", "2", "3", "4", "5", "6", "7", "8", "9",
                            "一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]]) or  # 标题第一个字有数字
                         any([i in box[1][:2] for i in [
                             "第一", "第二", "第三", "第四", "第五", "第六", "第七", "第八", "第九", "第十",
                             "附录"]]) or
                         any([i in box[1][:3] for i in [
                             "前言", "目录", "目次", "引言", "引用"]])) and \
                        (len(box[1]) >= 2 and
                         len(re.findall(r"[\u4e00-\u9fa5]+", box[1])) >= 1 and  # 标题中有中文
                         (re.findall(r"[0-9|a-z|A-Z|\u4e00-\u9fa5|、| ]+", box[1])[0] == box[1])):  # 标题中只有数字和中文英文
                    if re.findall(r"[0-9]+", box[1]) and len(re.findall(r"[0-9]+", box[1])[0]) > 2:  # 标题中数字大于两个字
                        texts[-1]["content"] += f"\n{box[1]}\n"
                    else:
                        # title = re.sub(r"第[0-9|一|二|三|四|五|六|七|八|九|十| ]{0,2}[节|章]|[0-9|第| ]+", "", box[1])  # 去掉标题中的序号
                        title = box[1]
                        if title in [i["title"] for i in texts]:
                            title_new = [i["title"] for i in texts if title == i["title"].split("_")[0]][-1]
                            title_index = title_new.split("_")
                            if len(title_index) >= 2:
                                title_index = int(title_index[-1])
                            else:
                                title_index = 0
                            title = f"{title}_{title_index+1}"
                        texts.append({"title": title, "content": ""})

                elif box[0][0] > min_x + width_50 and box[0][0] + box[0][2] < max_x - width_50:  # 该段前后均有缩进
                    texts[-1]["content"] += f"\n{box[1]}\n"
                elif box[0][0] > min_x + width_50:  # 该段前有缩进
                    texts[-1]["content"] += f"\n{box[1]}"
                elif box[0][0] + box[0][2] < max_x - width_50:  # 该段后有缩进
                    texts[-1]["content"] += f"{box[1]}\n"
                else:
                    texts[-1]["content"] += f"{box[1]}"
        texts = [{"title": re.sub(r'\n{1,100}', "\n", i["title"]).strip(),
                  "content": re.sub(r'\n{1,100}', "\n", i["content"]).strip()}
                 for i in texts if i["title"] or i["content"]]
        return texts

    @staticmethod
    def concat_box(boxes):
        sub_boxes = [[]]
        is_concat = False
        for i in range(len(boxes)):
            if len(boxes[i]) >= 2 and len(sub_boxes[-1]) == 0:  # 首次合并
                sub_boxes[-1].extend(boxes[i])
            elif len(boxes[i]) >= 2 and len(sub_boxes[-1]) != 0:
                for j in range(len(sub_boxes)):
                    if set(sub_boxes[j]) & set(boxes[i]):  # 有交集、合并
                        sub_boxes[j].extend(boxes[i])
                        is_concat = True
                        break
                else:  # 没有交集、不合并
                    sub_boxes.append(boxes[i])
        return sub_boxes, is_concat

    def merge_box_x_y(self, merged_x, merged_y, boxes, img_shape):
        """
        按照xy方向合并boxes
        """
        sub_boxes_x = copy.deepcopy(merged_x)  # 横向合并
        is_concat = True
        while is_concat:
            sub_boxes_x, is_concat = self.concat_box(sub_boxes_x)
        sub_boxes_x = [sorted(list(set(i)), key=lambda x: boxes[x][0][0]) for i in sub_boxes_x]  # 横向排序

        # 将单独的块进行合并
        merged_boxes = []
        for i in sub_boxes_x:
            merged_boxes.extend(i)
        single_boxes = [[i] for i in range(len(merged_x)) if i not in merged_boxes]
        sub_boxes = sub_boxes_x + single_boxes
        sub_boxes = [i for i in sub_boxes if i]
        sub_boxes = sorted(sub_boxes, key=lambda x: min(x))

        new_boxes = []
        for sub_box in sub_boxes:
            new_boxes.append([[
                min([boxes[i][0][0] for i in sub_box]),  # x
                min([boxes[i][0][1] for i in sub_box]),  # y
                max([boxes[i][0][0] + boxes[i][0][2] for i in sub_box]) - min([boxes[i][0][0] for i in sub_box]),
                min([boxes[i][0][1] + boxes[i][0][3] for i in sub_box]) - min([boxes[i][0][1] for i in sub_box])
            ], "".join([boxes[i][1] for i in sub_box])])

        if img_shape[1] > img_shape[0]:  # 横向页面
            new_boxes = self.split_box(new_boxes)
        else:
            new_boxes = [sorted(new_boxes, key=lambda x: x[0][1])]
        return new_boxes

    @staticmethod
    def split_box(boxes):
        """
        将boxes按照x方向分割成多栏
        """
        split_x = 0
        new_boxes = []
        boxes = sorted(boxes, key=lambda x: x[0][0])
        for index, box in enumerate(boxes):
            if index == 0:  # 第一次添加
                new_boxes.append([box])
                split_x = box[0][0] + box[0][2] + 3 * box[0][3]
            elif all([i[0][0] > split_x for i in boxes[index:]]):  # 之后的所有box的x坐标均大于split_x，分栏
                new_boxes.append([box])
                if box[0][0] + box[0][2] + 3 * box[0][3] > split_x:
                    split_x = box[0][0] + box[0][2] + 3 * box[0][3]
            else:
                new_boxes[-1].append(box)
                if box[0][0] + box[0][2] + 3 * box[0][3] > split_x:
                    split_x = box[0][0] + box[0][2] + 3 * box[0][3]

        new_boxes_sorted = []
        for index, box in enumerate(new_boxes):  # 对于每一个分栏里的数据进行竖向排序
            new_boxes_sorted.append(sorted(box, key=lambda x: x[0][1]))
        return new_boxes_sorted

    # def merge_text(self, merged_x, merged_y, boxes):
    #     """
    #     合并文字
    #     """
    #     sub_boxes_x = copy.deepcopy(merged_x)  # 横向合并
    #     is_concat = True
    #     while is_concat:
    #         sub_boxes_x, is_concat = self.concat_box(sub_boxes_x)
    #     sub_boxes_x = [sorted(list(set(i)), key=lambda x: boxes[x][0][0]) for i in sub_boxes_x]  # 横向排序
    #
    #     # 将单独的块进行合并
    #     merged_boxes = []
    #     for i in sub_boxes_x:
    #         merged_boxes.extend(i)
    #     single_boxes = [[i] for i in range(len(merged_x)) if i not in merged_boxes]
    #     sub_boxes = sub_boxes_x + single_boxes
    #     sub_boxes = [i for i in sub_boxes if i]
    #     sub_boxes = sorted(sub_boxes, key=lambda x: min(x))
    #
    #     all_text = ""
    #     for index, sub_box in enumerate(sub_boxes):
    #         text = ""
    #         draw_box = [99999, 99999]
    #         for i in sub_box:
    #             if i == 99999:
    #                 text += "\n"
    #                 all_text += "\n"
    #                 continue
    #             else:
    #                 text += " "
    #                 all_text += " "
    #             text += boxes[i][1]
    #             all_text += boxes[i][1]
    #             draw_box[0] = min(draw_box[0], boxes[i][0][0])
    #             draw_box[1] = min(draw_box[1], boxes[i][0][1])
    #         sub_boxes[index] = [draw_box, text.strip()]
    #         all_text += "\n"
    #     return all_text.replace("\n\n", "\n"), sub_boxes
