# -*- coding: UTF-8 -*-
"""
Created on 2018年11月15日
@author: Leo
@file: DingDingNotification
"""
# Python内置库
import json
import time

# Python第三方库
import asks
import curio

# 项目内部库
from DataVision.LoggerHandler.logger import VisionLogger

# asks配置
asks.init('curio')

# 日志路径
LOGGER_PATH = '../../DataVision/LoggerConfig/logger_config.yaml'

# 消息类型
MSG_TYPE_LIST = \
            ["text", "link", "markdown", "single_actionCard", "multiple_actionCard", "feedCard"]


class DingDingSender(object):

    def __init__(self, config_path: str = ""):
        """
        钉钉监控消息发布
        :param config_path: 配置文件目录 默认在LoggerConfig中
        """
        # 日志
        self._logger = VisionLogger(LOGGER_PATH)

        # 配置文件目录
        self._path = config_path
        if self._path == "":
            self._path = ".././LoggerConfig/logger_notification_config.json"

        # 加载配置文件
        dingding_config = self._load_config_from_json()
        self._req_url = dingding_config['robot_url'] + dingding_config['robot_token']

        # 默认请求
        self._header = {"Content-Type": "application/json;charset=utf-8"}

        # 统计发送次数和频率
        self.times = 0
        self.start_time = time.time()

    def _load_config_from_json(self) -> dict:
        return json.load(open(self._path, 'r'))['DingDing']

    @staticmethod
    def check_blank(content):
        """
        非空字符串
        :param content: 字符串
        :return: 非空 - True，空 - False
        """
        if content and content.strip():
            return True
        else:
            return False

    async def send_message(self, msg_type: str, **msg_kwargs):
        """
        发送消息
        :param msg_type 消息类型
        :param msg_kwargs: 其他参数
        :return: 接口返回的结果
        一、http(s)请求返回302，被网关层给拦截，一分钟只能发送20条，超过被加入黑名单5分钟。
        二、http(s)请求返回200，需要根据http body中的json字符，其中errorCode和errorMsg细分如下：
        String PARAM_ERROR = _300001_;   参数错误_
        String MSG_TOO_LONG = _101002_;   内容太长_
        String MSG_TOOMUCH = _130101_;    发送太快_
        String MSG_CONTENT_FORBID = _300004_;   内容不合法_
        String SYSTEM_ERROR = _1001_;     系统错误
        """
        message = self.make_message(msgtype=msg_type, **msg_kwargs)
        if message is not None:
            print(json.dumps(message, ensure_ascii=False, indent=4))
            try:
                self.times += 1
                if self.times % 20 == 0:
                    if time.time() - self.start_time < 60:
                        self._logger.vision_logger(level="DEBUG",
                                                   log_msg="钉钉官方限制每个机器人每分钟最多发送20条，当前消息发送频率已达到限制条件，休眠一分钟")
                        time.sleep(60)
                    self.start_time = time.time()
                # 发送
                response = await asks.post(self._req_url, headers=self._header, json=message)
                json_response = json.loads(response.content.decode("UTF-8"))
                if json_response['errcode'] == 0:
                    return True
                else:
                    print(json_response)
            except BaseException as err:
                self._logger.vision_logger(level="ERROR", log_msg=str(err))
                # TODO 当钉钉报警消息无法发送时 则同时发送到Redis和邮箱(邮箱地址通过配置文件进行配置)
        else:
            self._logger.vision_logger(level="ERROR", log_msg="报警消息发送失败!请检查消息格式后重新发送!")

    def make_message(self, msgtype: str, **msg_kwargs) -> dict:
        """
        :param msgtype 消息类型
        :param msg_kwargs: 其他参数如下
            content: 文本内容
            at_mobiles: 需要通知的联系人的手机号码(需要通讯录里有且开通了钉钉的)
            is_at_all: 是否需要通知全部人
            title: 文章或者卡片的标题
            message_url: link信息来源URL
            pic_url： link信息的封面图
            hide_avatar: 是否隐藏发送人的头像 0-正常发消息者头像,1-隐藏发消息者头像
            btn_orientation: 0-按钮竖直排列，1-按钮横向排列
            single_title: actionCard的参数 标题
            single_url: actionCard的参数 链接URL
            btns: actionCard不同按钮的实现功能 (包括以下参数title-按钮名称, actionURL-点击按钮触发的URL)
            links: feedCard的参数 (包括以下参数title-标题, messageURL-点击单条信息到跳转链接, picURL-单条信息后面图片的URL)
        :return 返回消息体(如果出错则返回的是None值)

        1、纯文本信息:
        msgtype: str = "text" 必须
        text:
            content: str -> "" 必须
        at:
            atMobiles: list -> [] 默认为空list 不必须
            isAtAll: bool -> True/False 默认为False 不必须

        2、链接信息:
        msgtype: str = "link" 必须
        link:
            title: str = "" 必须
            text: str -> "" (消息内容。如果太长只会部分展示) 必须
            messageUrl: str -> "" 点击消息跳转的URL 必须
            picUrl: str -> "图片URL" 不必须

        3、markdown信息:
        msgtype: str = "markdown" 必须
        markdown:
            title: str = "" 首屏会话透出的展示内容 必须
            text: str -> "" markdown格式的消息 必须
        at:
            atMobiles: list -> [] 不必须
            isAtAll: bool -> True/False 不必须
        * markdown支持的语法
        参见钉钉开放文档:
            https://open-doc.dingtalk.com/docs/doc.htm?spm=a219a.7629140.0.0.66bc4a97qGb7sV&treeId=257&articleId=105735&docType=1#s2):

        4、整体跳转ActionCard类型
        msgtype: str = "actionCard" 必须
        actionCard:
            title: str = "" 首屏会话透出的展示内容 必须
            text: str = "" markdown格式的消息 必须
            singleTitle: str = "" 单个按钮的方案。(设置此项和singleURL后btns无效。)  必须
            singleURL: bool -> True/False 必须
            btnOrientation: str = "" 0-按钮竖直排列，1-按钮横向排列 不必须
            hideAvatar: str = "" 0-正常发消息者头像,1-隐藏发消息者头像 不必须

        5、独立跳转ActionCard类型
        msgtype: str = "actionCard" 必须
        actionCard:
            title: str = "" 首屏会话透出的展示内容 必须
            text: str = "" markdown格式的消息 必须
            btns: list -> [] 按钮的信息可以嵌套多个 必须：
                title-按钮名称
                actionURL-点击按钮触发的URL
            btnOrientation: str = "" 0-按钮竖直排列，1-按钮横向排列 不必须
            hideAvatar: str = "" 0-正常发消息者头像,1-隐藏发消息者头像 不必须

        6、FeedCard类型
        msgtype: str = "feedCard" 必须
        feedCard: dict[list]
            title-标题
            messageURL-点击单条信息到跳转链接
            picURL-单条信息后面图片的URL
        例:
        {
            "msgtype": "feedCard"
            "feedCard: {
                "links": [
                    {"title": "", "messageURL": "", "picURL": ""}
                    ...
                    {"title": "", "messageURL": "", "picURL": ""}
                ]
            }
        }
        """
        # 判断消息类型, 选择对应的消息体构造
        if msgtype not in MSG_TYPE_LIST:
            self._logger.vision_logger(level="ERROR", log_msg="msgtype参数不存在!")
        else:
            if msgtype == "text":
                return self._text_message(**msg_kwargs)
            elif msgtype == "link":
                return self._link_message(**msg_kwargs)
            elif msgtype == "markdown":
                return self._markdown_message(**msg_kwargs)
            elif msgtype == "single_actionCard":
                return self._single_action_card_message(**msg_kwargs)
            elif msgtype == "multiple_actionCard":
                return self._multiple_action_card_message(**msg_kwargs)
            elif msgtype == "feedCard":
                return self._feed_card_message(**msg_kwargs)
            else:
                self._logger.vision_logger(level="ERROR", log_msg="错误的msgtype类型!")

    def _text_message(self, **msg_kwargs):
        # 参数校验
        content = msg_kwargs.get('content')
        if content is None or self.check_blank(content=content) is not True:
            self._logger.vision_logger(level="ERROR", log_msg="content参数不能为空或参数的值不能为空!")
            return
        mobiles = msg_kwargs.get('at_mobiles')
        if mobiles is None:
            mobiles = []
        is_at_all = msg_kwargs.get('is_at_all')
        if is_at_all is None:
            is_at_all = False
        # 构造json
        msg_json = {
            "msgtype": "text",
            "text": {"content": content},
            "at": {"atMobiles": mobiles, "isAtAll": is_at_all}
        }
        return msg_json

    def _link_message(self, **msg_kwargs):
        # 参数校验
        title = msg_kwargs.get('title')
        if title is None or self.check_blank(content=title) is not True:
            self._logger.vision_logger(level="ERROR", log_msg="title参数不能为空或参数的值不能为空!")
            return
        text = msg_kwargs.get('text')
        if text is None or self.check_blank(content=text) is not True:
            self._logger.vision_logger(level="ERROR", log_msg="text参数不能为空或参数的值不能为空!")
            return
        message_url = msg_kwargs.get('message_url')
        if message_url is None or self.check_blank(content=message_url) is not True:
            self._logger.vision_logger(level="ERROR", log_msg="message_url参数不能为空或参数的值不能为空!")
            return
        pic_url = msg_kwargs.get('pic_url')
        if pic_url is None:
            pic_url = ""
        # 构造json
        msg_json = {
            "msgtype": "link",
            "link": {
                "title": title,
                "text": text,
                "messageUrl": message_url,
                "picUrl": pic_url
            }
        }
        return msg_json

    def _markdown_message(self, **msg_kwargs):
        # 参数校验
        title = msg_kwargs.get('title')
        if title is None or self.check_blank(content=title) is not True:
            self._logger.vision_logger(level="ERROR", log_msg="title参数不能为空或参数的值不能为空!")
            return
        text = msg_kwargs.get('text')
        if text is None or self.check_blank(content=text) is not True:
            self._logger.vision_logger(level="ERROR", log_msg="text参数不能为空或参数的值不能为空!")
            return
        mobiles = msg_kwargs.get('at_mobiles')
        if mobiles is None:
            mobiles = []
        is_at_all = msg_kwargs.get('is_at_all')
        if is_at_all is None:
            is_at_all = False
        # 构造json
        msg_json = {
            "msgtype": "markdown",
            "markdown": {"title": title, "text": text},
            "at": {"atMobiles": mobiles, "isAtAll": is_at_all}
        }
        return msg_json

    def _single_action_card_message(self, **msg_kwargs):
        # 参数校验
        title = msg_kwargs.get('title')
        if title is None or self.check_blank(content=title) is not True:
            self._logger.vision_logger(level="ERROR", log_msg="title参数不能为空或参数的值不能为空!")
            return
        text = msg_kwargs.get('text')
        if text is None or self.check_blank(content=text) is not True:
            self._logger.vision_logger(level="ERROR", log_msg="text参数不能为空或参数的值不能为空!")
            return
        single_title = msg_kwargs.get('single_title')
        if single_title is None or self.check_blank(content=single_title) is not True:
            self._logger.vision_logger(level="ERROR", log_msg="single_title参数不能为空或参数的值不能为空!")
            return
        single_url = msg_kwargs.get('single_url')
        if single_url is None or self.check_blank(content=single_url) is not True:
            self._logger.vision_logger(level="ERROR", log_msg="single_url参数不能为空或参数的值不能为空!")
            return
        hide_avatar = msg_kwargs.get('hide_avatar')
        if hide_avatar is None:
            hide_avatar = "0"
        btn_orientation = msg_kwargs.get('btn_orientation')
        if btn_orientation is None:
            btn_orientation = "0"
        # 构造json
        msg_json = {
            "msgtype": "actionCard",
            "actionCard": {
                "title": title,
                "text": text,
                "hideAvatar": hide_avatar,
                "btnOrientation": btn_orientation,
                "singleTitle": single_title,
                "singleURL": single_url
            }
        }
        return msg_json

    def _multiple_action_card_message(self, **msg_kwargs):
        # 参数校验
        title = msg_kwargs.get('title')
        if title is None or self.check_blank(content=title) is not True:
            self._logger.vision_logger(level="ERROR", log_msg="title参数不能为空或参数的值不能为空!")
            return
        text = msg_kwargs.get('text')
        if text is None or self.check_blank(content=text) is not True:
            self._logger.vision_logger(level="ERROR", log_msg="text参数不能为空或参数的值不能为空!")
            return
        hide_avatar = msg_kwargs.get('hide_avatar')
        if hide_avatar is None:
            hide_avatar = "0"
        btn_orientation = msg_kwargs.get('btn_orientation')
        if btn_orientation is None:
            btn_orientation = "0"
        btn_list = msg_kwargs.get('btns')
        if btn_list is None:
            self._logger.vision_logger(level="ERROR", log_msg="btn_s参数不能为空!")
            return
        if isinstance(btn_list, list) is not True:
            self._logger.vision_logger(level="ERROR", log_msg="btn_s参数类型不正确!")
            return
        # 构造json
        msg_json = {
            "msgtype": "actionCard",
            "actionCard": {
                "title": title,
                "text": text,
                "hideAvatar": hide_avatar,
                "btnOrientation": btn_orientation,
                "btns": btn_list
            }
        }
        return msg_json

    def _feed_card_message(self, **msg_kwargs):
        link_list = msg_kwargs.get('links')
        if link_list is None:
            self._logger.vision_logger(level="ERROR", log_msg="links参数不能为空!")
            return
        if isinstance(link_list, list) is not True:
            self._logger.vision_logger(level="ERROR", log_msg="links参数类型不正确!")
            return
        msg_json = {
            "msgtype": "feedCard",
            "feedCard": {
                "links": link_list
            }
        }
        return msg_json


def send(msg_type: str, **msg_kwargs):
    """
    :param msg_type 消息类型
    :param msg_kwargs: 其他参数
    :return:
    """
    dingding = DingDingSender()
    curio.run(dingding.send_message(msg_type=msg_type, **msg_kwargs))


if __name__ == '__main__':
    send(msg_type="text", content="", at_mobiles=[], is_at_all=False)
