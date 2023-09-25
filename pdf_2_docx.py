from pdf2docx import Converter

pdf_file = 'data/type_0/新集村棚改项目.pdf'
docx_file = 'data/word/新集村棚改项目.docx'
cv = Converter(pdf_file)
cv.convert(docx_file, start=0, end=None)
cv.close()
