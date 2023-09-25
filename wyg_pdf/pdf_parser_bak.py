"""Loader that loads image files."""
from paddleocr import PaddleOCR, PPStructure
from tqdm.auto import tqdm
import os
import io
import cv2
import fitz
from PIL import Image
import numpy as np
from wyg_pdf.utils import boxes_connector
import re
import pandas as pd
import math


class UnstructuredPPStructurePDF(object):
    """
    结合PPStructure进行版面分析与PPOCR，将pdf文件解析为文本
    * 将pdf转换为png
    * 版面分析去除水印、页眉、页脚等非正文文本
    * 判断pdf文件中文字是否可读
    * 如果文本不可读，OCR识别正文文字
    * 文本合并、整理
    {
        name: name,
        alias: alias,
        content: [
            {
                title: title,
                content: content
            }
        ]
    }
    """

    def __init__(self):
        self.pp_structure = PPStructure(show_log=False, image_orientation=False)
        self.ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)

    def judge_pdf_text(self, docs):
        """
        判断pdf有没有文字版水印，如果有，后续直接去除
        """
        texts = []
        for i in range(docs.page_count):
            page = docs[i]
            text = page.get_text("")
            texts.append(text)

        texts = list(set([i for i in texts if i]))
        if len(texts) == 1 and len(texts[0].replace(" ", "")) <= 100:  # 文字全是水印
            return "watermark"
        else:
            return "no watermark"

    def concat_image(self, page):
        page_dict = page.get_text("dict")
        # 创建一个空白的PIL图像对象，大小为拼接后的图片大小
        scaling = 1000 / page_dict["height"]  # 缩放比例
        stitched = Image.fromarray(
            np.uint8(np.full((int(page_dict["height"] * scaling), int(page_dict["width"] * scaling), 3), 255)))
        # stitched = Image.new("RGB", (int(page_dict["width"]) * 4, int(page_dict["height"]) * 4))
        for block in page_dict["blocks"]:
            if "image" in block.keys():
                bytes_stream = io.BytesIO(block["image"])
                pil_img = Image.open(bytes_stream).resize(
                    (int((block["bbox"][2] - block["bbox"][0]) * scaling),
                     int((block["bbox"][3] - block["bbox"][1]) * scaling)))
                stitched.paste(pil_img, (
                    int(block["bbox"][0] * scaling),
                    int(block["bbox"][1] * scaling)))  # 粘贴到空白图像上，位置为(x_offset, y_offset)
        img = cv2.cvtColor(np.asarray(stitched), cv2.COLOR_RGB2BGR)
        return img

    def read_pdf_image(self, page):
        page_dict = page.get_text("dict")
        # 创建一个空白的PIL图像对象，大小为拼接后的图片大小
        scaling = 1000 / page_dict["height"]  # 缩放比例
        mat = fitz.Matrix(scaling, scaling)
        pix = page.get_pixmap(matrix=mat)
        arr = np.frombuffer(pix.samples, dtype=np.uint8)  # create 1D array
        img = arr.reshape(pix.height, pix.width, pix.n).copy()  # reshape array
        return img

    @staticmethod
    def get_real_rotation_flag(rect_list):
        real_rect_count = 0
        rect_big_list = []
        rect_small_list = []
        w_div_h_sum_big = []
        w_div_h_sum_small = []
        need_check_count = 0
        need_check_split = []
        need_check_split_w_div_h = []
        for rect in rect_list:
            p0 = rect[0]
            p1 = rect[1]
            p2 = rect[2]
            p3 = rect[3]
            width = abs(p1[0] - p0[0])
            height = abs(p3[1] - p0[1])
            if height == 0:
                continue
            w_div_h = width / height
            if w_div_h >= 100:
                need_check_split.append(rect)
                need_check_split_w_div_h.append(w_div_h)
                need_check_count += 1

            if 5 <= w_div_h <= 50:
                real_rect_count += 1
                rect_big_list.append(rect)
                w_div_h_sum_big.append(w_div_h)

            if 0.04 <= w_div_h <= 0.2:
                real_rect_count -= 1
                rect_small_list.append(rect)
                w_div_h_sum_small.append(w_div_h)
        flag = False
        if need_check_count > 0:
            flag = True
        if real_rect_count > 0:
            ret_rect = rect_big_list
            w_div_h_mean = np.mean(w_div_h_sum_big)
        else:
            ret_rect = rect_small_list
            w_div_h_mean = np.mean(w_div_h_sum_small)

        if w_div_h_mean >= 1.5:
            return 1, ret_rect, flag
        else:
            return 0, ret_rect, flag

    @staticmethod
    def crop_image(rect, image):
        """
        裁剪图片
        """
        p0 = rect[0]
        p1 = rect[1]
        p2 = rect[2]
        p3 = rect[3]
        crop = image[int(p0[1]):int(p2[1]), int(p0[0]):int(p2[0])]
        return crop

    @staticmethod
    def get_rect_angle(rects):
        """
        计算检测框的倾斜角度，并返回中位数
        """
        angles = []
        for rect in rects:
            if rect[3][0] - rect[0][0] == 0:
                angles.append(0)
                continue
            angle = 90 + (math.atan((rect[3][1] - rect[0][1]) / (rect[3][0] - rect[0][0])) * 180 / math.pi)
            if angle >= 90:
                angle = angle - 180
            angles.append(angle)
        if angles:
            angles = sorted(angles)
            return angles[int(len(angles) / 2)]
        else:
            return 0

    @staticmethod
    def rotate_bound_white_bg(image, angle):
        """
        旋转angle角度，缺失背景白色（255, 255, 255）填充
        """
        (h, w) = image.shape[:2]
        (cX, cY) = (w // 2, h // 2)

        M = cv2.getRotationMatrix2D((cX, cY), -angle, 1.0)
        cos = np.abs(M[0, 0])
        sin = np.abs(M[0, 1])

        nW = int((h * sin) + (w * cos))
        nH = int((h * cos) + (w * sin))

        M[0, 2] += (nW / 2) - cX
        M[1, 2] += (nH / 2) - cY
        return cv2.warpAffine(image, M, (nW, nH), borderValue=(255, 255, 255))

    def get_img_real_angle(self, image):
        """
        计算图片角度
        """
        ret_angle, angle = 0, 0
        rect_list = self.ocr.ocr(image, rec=False)
        rect_list = rect_list[0]
        if rect_list != [[]]:
            except_flag = False
            real_angle_flag, rect_good, flag = self.get_real_rotation_flag(
                rect_list)
            angle = self.get_rect_angle(rect_good)
            angle_cls_count = {'0': 0}
            for rect_crop in rect_good:
                image_crop = self.crop_image(rect_crop, image)
                if any([i == 0 for i in image_crop.shape]):
                    continue
                angle_cls = self.ocr.ocr(
                    image_crop, det=False, rec=False, cls=True)
                if angle_cls[0][0][1] >= 0.95:
                    angle_cls_count[angle_cls[0][0][0]] = angle_cls_count.get(
                        angle_cls[0][0][0], 0) + 1
            angle_cls = sorted(angle_cls_count.items(), key=lambda x: x[1])[-1][0]

        else:
            return 0
        if angle_cls == '0':
            if real_angle_flag:
                ret_angle = 0
            else:
                ret_angle = 270
                if not except_flag:
                    try:
                        anticlockwise_90 = self.rotate_bound_white_bg(image_crop, 90)
                        angle_cls = self.ocr.ocr(anticlockwise_90, det=False, rec=False, cls=True)
                        if angle_cls[0][0][0] == '0':
                            ret_angle = 270
                        if angle_cls[0][0][0] == '180':
                            ret_angle = 90
                    except:
                        ret_angle = 0
        if angle_cls[0][0][0] == '180':
            if real_angle_flag:
                ret_angle = 180
            else:
                ret_angle = 90
        return ret_angle + angle, rect_list

    def rotate_image(self, img):
        """
        检测图片是否有旋转，如果有，旋正图片
        """
        angle, rect_list = self.get_img_real_angle(img)
        h, w = img.shape[:2]
        cX, cY = (w // 2, h // 2)

        # 提取旋转矩阵 sin cos -sin -cos
        M = cv2.getRotationMatrix2D((cX, cY), angle, 1.0)
        cos = np.abs(M[0, 0])
        sin = np.abs(M[0, 1])

        # 计算图像的新边界尺寸
        nW = int((h * sin) + (w * cos))
        nH = int((h * cos) + (w * sin))

        # 调整旋转矩阵的中心点
        M[0, 2] += (nW / 2) - cX
        M[1, 2] += (nH / 2) - cY
        img = cv2.warpAffine(img, M, (nW, nH), borderValue=(255, 255, 255))
        return img

    def get_content_by_img(self, docs, watermark_flag):
        ocr_res_list = []
        for i in tqdm(range(docs.page_count), total=docs.page_count, desc="解析pdf"):
            page = docs.load_page(i)
            if watermark_flag == "watermark":  # 有文字版水印
                img = self.concat_image(page)
            else:  # 没有文字版水印，直接读取当前图片
                img = self.read_pdf_image(page)
            img = self.rotate_image(img)  # 旋转图片
            # Image.fromarray(img).save(os.path.join(tmp_file_path, f"{i}_original.png"))
            structure_res = self.pp_structure(img)  # 分析版面
            img, structure_with_text = self.mask_change_img(img, structure_res)
            # Image.fromarray(img).save(os.path.join(tmp_file_path, f"{i}_mask.png"))

            ocr_res = self.ocr.ocr(img, rec=True)[0]  # OCR
            ocr_res.extend(structure_with_text)

            ocr_res = boxes_connector.merge_box(ocr_res, img.shape)  # 横向拼接
            ocr_res_list.extend(ocr_res)

            # if i >= 10:
            #     break

        ocr_text = boxes_connector.merge_text(ocr_res_list)  # 拼接成文字
        return ocr_text

    def mask_img(self, img, rect):
        """
        将rect中的图片进行mask
        """
        mask_img = np.full((rect[3] - rect[1], rect[2] - rect[0], 3), 255, dtype=np.uint8)
        img[rect[1]:rect[3], rect[0]:rect[2]] = mask_img
        return img

    def mask_change_img(self, img, structure_res):
        """
        将图片中的header、footer进行mask
        将图片中的table进行mask，并将表格解析成markdown补充到原有位置
        """
        structure_with_text = []
        for structure in structure_res:
            if structure["type"] in ("header", "footer", "table"):
                img = self.mask_img(img, structure["bbox"])
            if structure["type"] == "table":
                table_html = structure["res"]["html"]
                try:
                    structure["md"] = re.sub(r" |nan|-|:", "",
                                             pd.read_html(table_html, header=0)[0].to_markdown(index=False))
                except:
                    continue
                structure_with_text.append(
                    [[
                        [structure["bbox"][0], structure["bbox"][1]],
                        [structure["bbox"][2], structure["bbox"][1]],
                        [structure["bbox"][2], structure["bbox"][3]],
                        [structure["bbox"][0], structure["bbox"][3]]],
                        (f"\ntable<{structure['md']}>table\n", 1.0)]
                )
        return img, structure_with_text

    def pdf_ocr_txt(self, filepath):
        # tmp_file_path = os.path.join(".".join(filepath.split(".")[:-1]))
        # if not os.path.exists(tmp_file_path):
        #     os.makedirs(tmp_file_path)
        docs = fitz.open(filepath)
        watermark_flag = self.judge_pdf_text(docs)  # 判断pdf文件是文字版还是图片
        return self.get_content_by_img(docs, watermark_flag)


if __name__ == "__main__":
    import sys

    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    filepath = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "type_0/综合交通换乘中心全过程设计.pdf")
    pp_structure_pdf = UnstructuredPPStructurePDF()
    docs = pp_structure_pdf.pdf_ocr_txt(filepath)
    for doc in docs:
        print(doc)
