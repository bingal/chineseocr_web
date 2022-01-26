#!/usr/bin/python
# encoding: utf-8
import os
import sys

BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_PATH)

import tornado.web
import tornado.httpserver
import tornado.ioloop
from tornado.web import StaticFileHandler
from backend.tools.get_host_ip import host_ip
from backend.webInterface import tr_run
from backend.webInterface import tr_index
from backend.tools import log
import logging
logger = logging.getLogger(log.LOGGER_ROOT_NAME+'.'+__name__)

current_path = os.path.dirname(__file__)
settings = dict(
    # debug=True,
    static_path=os.path.join(current_path, "dist/chineseocr_lite_fontend")  # 配置静态文件路径
)


def make_app():
    return tornado.web.Application([
        (r"/ocr/api/tr-run/", tr_run.TrRun),
        (r"/api/tr-run/", tr_run.TrRun),
        (r"/ocr/", tr_index.Index),
        (r"/", tr_index.Index),
        (r"/ocr/(.*)", StaticFileHandler,
         {"path": os.path.join(current_path, "dist/chineseocr_lite_fontend"), "default_filename": "index.html"}),
        (r"/(.*)", StaticFileHandler,
         {"path": os.path.join(current_path, "dist/chineseocr_lite_fontend"), "default_filename": "index.html"}),

    ], **settings)


if __name__ == "__main__":
    env_port = os.getenv('PORT')
    port = env_port if env_port else 8080
    app = make_app()
    server = tornado.httpserver.HTTPServer(app)
    # server.listen(port)
    server.bind(port)
    server.start(1)
    print(f'server is running: {host_ip()}:{port}')

    # tornado.ioloop.IOLoop.instance().start()
    tornado.ioloop.IOLoop.current().start()
