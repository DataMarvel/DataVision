# -*- coding: UTF-8 -*-
"""
Created on 2018年11月15日
@author: Leo
@file: EmailNotification
"""
# Python内置库
import json
import socket
import asyncio
import mimetypes
from typing import (
    Union,
    Optional,
    Dict,
    List,
    Any
)
from email import encoders
from email.header import Header
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.utils import parseaddr, formataddr
from email.mime.multipart import MIMEMultipart
from email.mime.nonmultipart import MIMENonMultipart


# Python第三方库
import aiosmtplib

# 项目内部库
from DataVision.LoggerHandler.logger import VisionLogger

# 日志路径
LOGGER_PATH = '../../DataVision/LoggerConfig/logger_config.yaml'


def get_current_ip() -> str:
    """
    获取当前IP地址
    :return: ip地址
    """
    return [(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close())
            for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]
            ][0][1]


class EmailSender(object):
    """
    使用后发送邮件会被绑定在`app对象`上,支持协程`send_email`,
    也支持方法`send_email_nowait`,其中`send_email_nowait`意为将任务交给协程发送而不等待发送完毕,
    会返回发送的task.
    """

    def __init__(self, loop, config_path: str = "") -> None:
        """
        异步邮件发送器
        :param loop: 事件循环 [Windows下显示 <class 'asyncio.windows_events._WindowsSelectorEventLoop'>]
        :param config_path: 配置文件目录 默认在LoggerConfig中
        """
        # 日志
        self._logger = VisionLogger(LOGGER_PATH)

        # 配置文件目录
        self._path = config_path
        if self._path == "":
            self._path = ".././LoggerConfig/logger_notification_config.json"

        # 加载配置文件
        mail_config = self._load_config_from_json()
        self._mail_host = mail_config['mail_host']
        self._mail_port = mail_config['mail_port']
        self._mail_user = mail_config['mail_user']
        self._mail_password = mail_config['mail_password']
        self._mail_suffix = mail_config['mail_suffix']

        # 基本变量
        self.smtp = None
        self.loop = loop
        self.loop.run_until_complete(self.stmp_connection())

    def _load_config_from_json(self) -> dict:
        return json.load(open(self._path, 'r'))['Email']

    async def stmp_connection(self):
        self.smtp = aiosmtplib.SMTP(
            loop=self.loop,
            hostname=self._mail_host,
            port=self._mail_port,
            use_tls=True
        )
        await self.smtp.connect()
        await self.smtp.login(
            self._mail_user, self._mail_password
        )
        self._logger.vision_logger(level="INFO", log_msg="邮件服务器连接成功!")

    async def stmp_close(self):
        self.smtp.close()
        self.smtp = None
        self._logger.vision_logger(level="INFO", log_msg="邮件服务器关闭成功!")
        return True

    async def send_email(self,
                         target_list: Union[List[str], str],
                         subject: str,
                         content: str,
                         sender_name: Optional[str]=None,
                         c_c_list: Union[List[str], str, None]=None,
                         html: bool=False,
                         msgimgs: Optional[Dict[str, str]]=None,
                         attachments: Optional[Dict[str, str]]=None)->Any:
        """执行发送email的动作.
        Parameters:
            target_list (Union[List[str], str]): - 接受者的信息列表,也可以是单独的一条信息
            c_c_list (Optional[List[str], str]): - 抄送者的信息列表,也可以是单独的一条信息
            subject (str): - 邮件主题
            content (str): - 邮件的文本内容
            sender_name (Optinal[str]): - 发送者的发送名,默认为None
            html (bool): - 又见文本是否是html形式的富文本,默认为False
            msgimgs (Optional[Dict[str, str]]): - html格式的文本中插入的图片
            attachments (Optional[Dict[str, str]]): - 附件中的文件,默认为None
        """
        if sender_name:
            sender = sender_name + "<" + "{}@{}".format(self._mail_user, self._mail_suffix) + ">"
        else:
            sender = "{}@{}".format(self._mail_user, self._mail_suffix)
        if isinstance(target_list, (list, tuple)):
            targetlist = tuple(target_list)
            targets = ", ".join(targetlist)
        elif isinstance(target_list, str):
            targets = target_list
        else:
            raise AttributeError("unsupport type for targetlist")

        if c_c_list:
            if isinstance(c_c_list, (list, tuple)):
                c_c_list = tuple(c_c_list)
                c_c = ", ".join(c_c_list)
            elif isinstance(c_c_list, str):
                c_c = c_c_list
            else:
                raise AttributeError("unsupport type for Cclist")
        else:
            c_c = None
        message = make_message(sender=sender,
                               targets=targets,
                               subject=subject,
                               content=content,
                               html=html,
                               c_c=c_c,
                               msgimgs=msgimgs,
                               attachments=attachments)
        return await self.smtp.send_message(message)

    def send_email_no_wait(self,
                           target_list: Union[List[str], str],
                           subject: str,
                           content: str,
                           sender_name: str=None,
                           c_c_list: Union[List[str], str, None]=None,
                           html: bool=False,
                           msgimgs: Optional[Dict[str, str]]=None,
                           attachments: Optional[Dict[str, str]]=None)->asyncio.Task:
        """执行发送email的动作但不等待而是继续执行下一步的操作.
        Parameters:
            target_list (Union[List[str], str]): - 接受者的信息列表,也可以是单独的一条信息
            c_c_list (Optional[List[str], str]): - 抄送者的信息列表,也可以是单独的一条信息
            subject (str): - 邮件主题
            content (str): - 邮件的文本内容
            sender_name (Optinal[str]): - 发送者的发送名,默认为None
            html (bool): - 又见文本是否是html形式的富文本,默认为False
            msgimgs (Optional[Dict[str, str]]): - html格式的文本中插入的图片
            attachments (Optional[Dict[str, str]]): - 附件中的文件,默认为None
        Return:
            (asyncio.Task): - 执行发送邮件的任务实例
        """
        task = asyncio.ensure_future(
            self.send_email(
                target_list=target_list,
                subject=subject,
                content=content,
                sender_name=sender_name,
                c_c_list=c_c_list,
                html=html,
                msgimgs=msgimgs,
                attachments=attachments
            )
        )
        return task


def format_addr(s: str)->str:
    """将地址信息格式化为`名字<地址>`的形式."""
    name, addr = parseaddr(s)
    return formataddr((Header(name, 'utf-8').encode(), addr))


def make_message(
        sender: str,
        targets: str,
        subject: str,
        content: str,
        html: bool=False,
        c_c: str=None,
        msgimgs: Optional[Dict[str, str]]=None,
        attachments: Optional[Dict[str, str]]=None)-> MIMEMultipart:
    """创建信息.
    创建信息通过html标志指定内容是html的富文本还是普通文本.默认为普通文本.
    如果是html形式,可以用以下形式插入图片:
    <img src="cid:image1.jpg">
    使用`msgimgs`定义插入的图片,默认为None.以字典的形式传入,键为文本中对应的cid值,
    此处要求是图片的带后缀名,值则是从图片中读出的字节序列.
    与之类似的是pics和files,他们用于设置附件中的图片或者附件
    Parameters:
        sender (str): - 发送者的信息
        targets (str): - 接受者的信息
        c_c (str): - 抄送者的信息
        subject (str): - 邮件主题
        content (str): - 邮件的文本内容
        html (bool): - 又见文本是否是html形式的富文本,默认为False
        msgimgs (Optional[Dict[str, str]]): - html格式的文本中插入的图片
        attachments (Optional[Dict[str, str]]): - 附件中的文件,默认为None
    Returns:
        (MIMEMultipart): - 没有设置发送者和收件者的邮件内容对象
    """
    msg = MIMEMultipart()
    msg['Subject'] = Header(subject, "utf-8").encode()
    msg['From'] = format_addr(sender)
    msg['To'] = targets
    if c_c:
        msg['Cc'] = c_c
    if html:
        text = MIMEText(content, 'html', 'utf-8')
        msg.attach(text)
        if msgimgs:
            for i, v in msgimgs.items():
                c_type, encoding = mimetypes.guess_type(i)
                _maintype, _subtype = c_type.split('/', 1)
                msg_image = MIMEImage(v, _subtype)
                msg_image.add_header('Content-ID', '<{}>'.format(i.split(".")[0]))
                msg_image.add_header('Content-Disposition', 'inline')
                msg.attach(msg_image)
    else:
        text = MIMEText(content, 'plain')
        msg.attach(text)
    if attachments:
        for name, file in attachments.items():
            attachment = MIMEAttachment(name, file)
            attachment.add_header('Content-Disposition', 'attachment', filename=name)
            msg.attach(attachment)
    return msg


class MIMEAttachment(MIMENonMultipart):
    def __init__(self, attache_name, _attachement_data,
                 _encoder=encoders.encode_base64, *, policy=None, **_params):
        """
        """
        ctype, encoding = mimetypes.guess_type(attache_name)
        if ctype is None or encoding is not None:
            ctype = 'application/octet-stream'
        _maintype, _subtype = ctype.split('/', 1)
        # if _subtype is None:
        #     raise TypeError('Could not guess image MIME subtype')
        MIMENonMultipart.__init__(self, _maintype, _subtype, policy=policy,
                                  **_params)
        self.set_payload(_attachement_data)
        _encoder(self)


# 异步发送邮件
def send(target_list: Union[List[str], str],
         subject: str,
         content: str,
         sender_name: str=None,
         c_c_list: Union[List[str], str, None]=None,
         html: bool=False,
         msgimgs: Optional[Dict[str, str]]=None,
         attachments: Optional[Dict[str, str]]=None):
    """
    Parameters:
            target_list (Union[List[str], str]): - 接受者的信息列表,也可以是单独的一条信息
            c_c_list (Optional[List[str], str]): - 抄送者的信息列表,也可以是单独的一条信息
            subject (str): - 邮件主题
            content (str): - 邮件的文本内容
            sender_name (Optinal[str]): - 发送者的发送名,默认为None
            html (bool): - 又见文本是否是html形式的富文本,默认为False
            msgimgs (Optional[Dict[str, str]]): - html格式的文本中插入的图片
            attachments (Optional[Dict[str, str]]): - 附件中的文件,默认为None
    """
    # 事件循环
    loop = asyncio.get_event_loop()
    s_m = EmailSender(loop=loop)
    # 运行异步
    loop.run_until_complete(
        s_m.send_email_no_wait(
            target_list=target_list,
            subject=subject,
            content=content,
            sender_name=sender_name,
            c_c_list=c_c_list,
            html=html,
            msgimgs=msgimgs,
            attachments=attachments
        )
    )
    loop.run_until_complete(s_m.stmp_close())


if __name__ == '__main__':
    send(target_list="379978424@qq.com",
         subject="测试报警 - DataVision",
         content="From DataVision",
         sender_name="监控报警邮件")
