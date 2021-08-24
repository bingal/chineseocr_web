#!/usr/bin/python
# encoding: utf-8
from config import max_post_time, dbnet_max_size, white_ips
import time
from model import OcrHandle
import tornado.web
import tornado.gen
import tornado.httpserver
import base64
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from io import BytesIO
import datetime
import json
import requests
from io import BytesIO

from backend.tools.np_encoder import NpEncoder
from backend.tools import log
import logging

logger = logging.getLogger(log.LOGGER_ROOT_NAME + '.' + __name__)

ocrhandle = OcrHandle()


request_time = {}
now_time = time.strftime("%Y-%m-%d", time.localtime(time.time()))


class TrRun(tornado.web.RequestHandler):
    '''
    使用 tr 的 run 方法
    '''

    def make_mask(self, points):
        left = min(map(lambda x: x[0], points))
        top = min(map(lambda x: x[1], points))
        right = max(map(lambda x: x[0], points))
        bottom = max(map(lambda x: x[1], points))
        mask = Image.new("RGBA", (right-left, bottom-top))
        drawer = ImageDraw.Draw(mask)
        drawer.polygon((points[0][0]-left, points[0][1]-top, points[1][0]-left, points[1][1]-top,
                       points[2][0]-left, points[2][1]-top, points[3][0]-left, points[3][1]-top), fill='black')
        return (left, top, right, bottom, mask)

    def do_mosaic(self, img, ocr_data, mosaic_words):
        matched_text = []
        not_matched_text = []
        im = img.copy()
        for it in ocr_data:
            pos = it[0]
            txt = it[1]
            if not mosaic_words:
                left, top, right, bottom, mask = self.make_mask(pos)
                region = im.crop((left, top, right, bottom))
                region = region.filter(ImageFilter.GaussianBlur(radius=10))
                im.paste(region, (left, top), mask=mask)
                matched_text.append(txt)
            else:
                for word in mosaic_words:
                    if word in txt:
                        left, top, right, bottom, mask = self.make_mask(pos)
                        region = im.crop((left, top, right, bottom))
                        region = region.filter(
                            ImageFilter.GaussianBlur(radius=5))
                        im.paste(region, (left, top), mask=mask)
                        matched_text.append(txt)
                        break
                else:
                    not_matched_text.append(txt)
        output_buffer = BytesIO()
        im.save(output_buffer, format='JPEG')
        byte_data = output_buffer.getvalue()
        img_detected_b64 = base64.b64encode(byte_data).decode('utf8')
        return {'matched_text': matched_text, 'not_matched_text': not_matched_text, 'mosaic_img': img_detected_b64}

    def do_mosaic_img_only(self, img, ocr_data, mosaic_words):
        matched_text = []
        not_matched_text = []
        im = img.copy()
        for it in ocr_data:
            pos = it[0]
            txt = it[1]
            if not mosaic_words:
                left, top, right, bottom, mask = self.make_mask(pos)
                region = im.crop((left, top, right, bottom))
                region = region.filter(ImageFilter.GaussianBlur(radius=10))
                im.paste(region, (left, top), mask=mask)
                matched_text.append(txt)
            else:
                for word in mosaic_words:
                    if word in txt:
                        left, top, right, bottom, mask = self.make_mask(pos)
                        region = im.crop((left, top, right, bottom))
                        region = region.filter(ImageFilter.GaussianBlur(radius=5))
                        im.paste(region, (left, top), mask=mask)
                        matched_text.append(txt)
                        break
                else:
                    not_matched_text.append(txt)
        # output_buffer = BytesIO()

        return im

    @tornado.gen.coroutine
    def get(self):
        self.set_header('content-type', 'application/json')
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")

        img_url = self.get_query_argument('url', '', strip=True)
        compress_size = self.get_query_argument('shortlen', '1200')
        mosaic_words = self.get_query_argument('keyword', '', strip=True)
        ext = 'jpg'
        img_fmts = {
            'jpg':'JPEG',
            'jpeg':'JPEG',
            'png':'PNG',
            'webp':'WEBP'
        }
        
        if not img_url:
            self.set_status(400)
            self.finish('参数 shortlen 错误')
            return
        tempurl = img_url.lower()
        tempurl = tempurl.split('?')[0]
        tempurl = tempurl.split('/')[-1]
        if '.' in tempurl:
            ext = tempurl.split('.')[-1]
        try:
            response = requests.get(
                img_url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36 Edg/92.0.902.62'}, timeout=30)
            img = Image.open(BytesIO(response.content))
        except Exception as e:
            self.set_status(400)
            self.finish('图片下载失败 {}'.format(e))
            return
        try:
            compress_size = int(compress_size)
        except Exception as e:
            self.set_status(400)
            self.finish('参数 shortlen 错误 {}'.format(e))
            return
        if mosaic_words:
            mosaic_words = mosaic_words.split(',')
        
        '''
        是否开启图片压缩
        默认为960px
        值为 0 时表示不开启压缩
        非 0 时则压缩到该值的大小
        '''
        short_size = compress_size
        if short_size < 64:
            self.set_status(400)
            self.finish('参数 shortlen 错误')
            return

        short_size = 32 * (short_size//32)

        img_w, img_h = img.size
        # 图片尺寸太小返回原图
        if max(img_w, img_h) < 400:
            self.set_header('content-type', 'image/{}'.format(img_fmts.get(ext, 'jpeg').lower()))
            output_buffer = BytesIO()
            img.save(output_buffer, format=img_fmts.get(ext, 'JPEG'))
            self.write(output_buffer.getvalue())
            return
        # 图片reize后长边过长，调整short_size
        if max(img_w, img_h) * (short_size * 1.0 / min(img_w, img_h)) > dbnet_max_size:
            short_size = int(dbnet_max_size * 1.0 * min(img_w, img_h) / max(img_w, img_h))
            # img_w_new = dbnet_max_size if img_w >= img_h else int(dbnet_max_size * img_w * 1.0 / img_h)
            # img_h_new = dbnet_max_size if img_w <= img_h else int(dbnet_max_size * img_h * 1.0 / img_w)
            # img = img.resize((img_w_new, img_h_new))
            # self.set_status(400)
            # self.finish('图片reize后长边过长，请调整短边尺寸, 最大值 {}, 目前是 {}'.format(dbnet_max_size), max(
            #     img_w, img_h) * (short_size * 1.0 / min(img_w, img_h)))
            # return


        res = ocrhandle.text_predict(img, short_size)

        mosaic_img = self.do_mosaic_img_only(img, res, mosaic_words)

        output_buffer = BytesIO()
        mosaic_img.save(output_buffer, format=img_fmts.get(ext, 'JPEG'))
        
        byte_data = output_buffer.getvalue()
        # Content-Type: image/jpeg
        self.set_header('content-type', 'image/{}'.format(img_fmts.get(ext, 'jpeg').lower()))
        # self.set_header('Content-Disposition', 'attachment;filename={}'.format(_filename))
        # with open(output_buffer, 'rb') as f:
        self.write(byte_data)
        self.finish()

    @tornado.gen.coroutine
    def post(self):
        '''

        :return:
        报错：
        400 没有请求参数

        '''
        start_time = time.time()
        short_size = 960
        global now_time
        global request_time
        # rt_img = self.get_argument('rt_img', '0')
        img_url = self.get_argument('url', None)
        img_up = self.request.files.get('file', None)
        img_b64 = self.get_argument('img', None)
        rt_origin = self.get_argument('rt_origin', '0')
        rt_ocr = self.get_argument('rt_ocr', '0')
        rt_mosaic = self.get_argument('rt_mosaic', '0')
        compress_size = self.get_argument('shortlen', None)
        mosaic_words = self.get_argument('keyword', None)

        if mosaic_words:
            mosaic_words = mosaic_words.split(',')

        # 判断是上传的图片还是base64
        self.set_header('content-type', 'application/json')
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST')
        
        up_image_type = None
        if img_url is not None and img_url.startswith('http'):
            try:
                response = requests.get(
                    img_url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36 Edg/92.0.902.62'}, timeout=30)
                img = Image.open(BytesIO(response.content))
            except Exception:
                self.finish(json.dumps(
                    {'code': 500, 'msg': '图片下载失败'}, cls=NpEncoder))
                return
        elif img_up is not None and len(img_up) > 0:
            img_up = img_up[0]
            up_image_type = img_up.content_type
            up_image_name = img_up.filename
            img = Image.open(BytesIO(img_up.body))
        elif img_b64 is not None:
            raw_image = base64.b64decode(img_b64.encode('utf8'))
            img = Image.open(BytesIO(raw_image))
        else:
            self.set_status(400)
            logger.error(json.dumps(
                {'code': 400, 'msg': '没有传入参数'}, cls=NpEncoder))
            self.finish(json.dumps(
                {'code': 400, 'msg': '没有传入参数'}, cls=NpEncoder))
            return

        try:
            if hasattr(img, '_getexif') and img._getexif() is not None:
                orientation = 274
                exif = dict(img._getexif().items())
                if orientation not in exif:
                    exif[orientation] = 0
                if exif[orientation] == 3:
                    img = img.rotate(180, expand=True)
                elif exif[orientation] == 6:
                    img = img.rotate(270, expand=True)
                elif exif[orientation] == 8:
                    img = img.rotate(90, expand=True)
        except Exception as ex:
            error_log = json.dumps(
                {'code': 400, 'msg': '产生了一点错误，请检查日志', 'err': str(ex)}, cls=NpEncoder)
            logger.error(error_log, exc_info=True)
            self.finish(error_log)
            return
        img = img.convert("RGB")

        time_now = time.strftime(
            "%Y-%m-%d-%H_%M_%S", time.localtime(time.time()))
        time_day = time.strftime("%Y-%m-%d", time.localtime(time.time()))
        if time_day != now_time:
            now_time = time_day
            request_time = {}
        #img.save("../web_imgs/{}.jpg".format(time_now))

        '''
        是否开启图片压缩
        默认为960px
        值为 0 时表示不开启压缩
        非 0 时则压缩到该值的大小
        '''
        res = []
        do_det = True
        remote_ip_now = self.request.remote_ip
        if remote_ip_now not in request_time:
            request_time[remote_ip_now] = 1
        elif request_time[remote_ip_now] > max_post_time - 1 and remote_ip_now not in white_ips:
            res.append("今天访问次数超过{}次！".format(max_post_time))
            do_det = False
        else:
            request_time[remote_ip_now] += 1

        if compress_size is not None:
            try:
                compress_size = int(compress_size)
            except ValueError as ex:
                # logger.error(exc_info=True)
                res.append("短边尺寸参数类型有误，只能是int类型")
                do_det = False
                # self.finish(json.dumps({'code': 400, 'msg': 'compress参数类型有误，只能是int类型'}, cls=NpEncoder))
                # return

            short_size = compress_size
            if short_size < 64:
                res.append("短边尺寸过小，请调整短边尺寸")
                do_det = False

            short_size = 32 * (short_size//32)

        img_w, img_h = img.size
        if max(img_w, img_h) * (short_size * 1.0 / min(img_w, img_h)) > dbnet_max_size:
            # logger.error(exc_info=True)
            short_size = int(dbnet_max_size * 1.0 * min(img_w, img_h) / max(img_w, img_h))
            # res.append("图片reize后长边过长，请调整短边尺寸")
            # do_det = False
            # self.finish(json.dumps({'code': 400, 'msg': '图片reize后长边过长，请调整短边尺寸'}, cls=NpEncoder))
            # return

        if do_det:

            res = ocrhandle.text_predict(img, short_size)

            img_detected = img.copy()
            img_draw = ImageDraw.Draw(img_detected)
            colors = ['red', 'green', 'blue', "purple"]

            for i, r in enumerate(res):
                rect, txt, confidence = r

                x1, y1, x2, y2, x3, y3, x4, y4 = rect.reshape(-1)
                size = max(min(x2-x1, y3-y2) // 2, 20)

                myfont = ImageFont.truetype("fangsong_GB2312.ttf", size=size)
                fillcolor = colors[i % len(colors)]
                img_draw.text((x1, y1 - size), str(i+1),
                              font=myfont, fill=fillcolor)
                for xy in [(x1, y1, x2, y2), (x2, y2, x3, y3), (x3, y3, x4, y4), (x4, y4, x1, y1)]:
                    img_draw.line(xy=xy, fill=colors[i % len(colors)], width=2)

            output_buffer = BytesIO()
            img_detected.save(output_buffer, format='JPEG')
            byte_data = output_buffer.getvalue()
            img_detected_b64 = base64.b64encode(byte_data).decode('utf8')

        else:
            output_buffer = BytesIO()
            img.save(output_buffer, format='JPEG')
            byte_data = output_buffer.getvalue()
            img_detected_b64 = base64.b64encode(byte_data).decode('utf8')

        log_info = {
            'ip': self.request.remote_ip,
            'return': res,
            'time': time_now,
            'mosaic_words': mosaic_words if mosaic_words else ''
        }
        logger.info(json.dumps(log_info, cls=NpEncoder))
        # 如果是传入url则把原始图片返回
        origin_img = ''
        if img_url is not None and img_url.startswith('http'):
            output_buffer = BytesIO()
            img.save(output_buffer, format='JPEG')
            byte_data = output_buffer.getvalue()
            origin_img = base64.b64encode(byte_data).decode('utf8')
        # 对文字模糊处理
        mosaic = {}
        mosaic_img = ''
        if do_det:
            mosaic = self.do_mosaic(img, res, mosaic_words)
            if rt_mosaic == '1':
                mosaic_img = mosaic.get('mosaic_img', '')
            try:
                del mosaic['mosaic_img']
            except Exception:
                pass
        if rt_ocr == '0':
            img_detected_b64 = ''
        if rt_origin == '0':
            origin_img = ''
        result = {'code': 200, 'msg': '成功',
                'data': {'ocr_img': img_detected_b64,
                         'ocr_info': res,
                         'mosaic_img': mosaic_img,
                         'origin_img': origin_img,
                         'speed_time': round(time.time() - start_time, 2),
                         'mosaic_info': mosaic}}
        

        # data:image/jpeg;base64,
        self.finish(json.dumps(
            result,
            cls=NpEncoder))
        return
