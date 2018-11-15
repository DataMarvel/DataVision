# -*- coding: UTF-8 -*-
"""
Created on 2018年11月15日
@author: Leo
@file: logger
日志模块
"""
# Python内置库
import os
import logging.config

# Python第三方库
import yaml


class VisionLogger(object):

    def __init__(self,
                 default_path='./LoggerConfig/logger_config.yaml',
                 default_level=logging.INFO):
        """
        "幻视" --> 日志模块
        :param default_path: Logger Yaml的默认路径
        :param default_level: Logger默认等级
        """
        if os.path.exists('vision') is not True:
            os.mkdir('vision')
        # 获取配置路径
        path = default_path
        if os.path.exists(path):
            with open(path, 'rt') as f:
                config = yaml.load(f.read())
                logging.config.dictConfig(config)
        else:
            logging.basicConfig(level=default_level)
            logging.error('路径不存在!')

    @staticmethod
    def get_logger():
        """
        使用的是默认的log模块输出
        :return: 返回logger对象
        """
        return logging.getLogger()

    def vision_logger(self, level='INFO', log_msg: str = ""):
        """
        带采集功能的日志
        """
        # 获取默认的logger
        logger = self.get_logger()
        # 分级输出
        if level == "DEBUG":
            logger.debug(log_msg)
        elif level == 'INFO':
            logger.info(log_msg)
        elif level == 'WARN':
            logger.warning(log_msg)
        elif level == 'ERROR':
            logger.error(log_msg)
        elif level == 'CRITICAL':
            logger.critical(log_msg)
        else:
            raise ValueError("日志等级不存在或者拼写错误!")
        # TODO 日志采集器的加载方法
