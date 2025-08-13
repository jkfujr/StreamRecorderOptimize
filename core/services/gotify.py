import asyncio
import httpx
import logging

"""Gotify模块

提供Gotify异步消息推送功能。可以直接传入IP、token、标题、消息和优先级等参数。

函数：
    push_gotify(ip, token, title, message, priority=1, extras=None, max_retries=3, retry_delay=3)
        异步推送消息到Gotify。
        参数：
            ip: Gotify服务器的IP地址（可以包含协议）。
            token: Gotify服务器的token。
            title: 消息标题。
            message: 消息内容。
            priority: 消息优先级，默认值为1。
            extras: 消息附加信息字典，支持bigImageUrl等，默认值为None。
            max_retries: 最大重试次数，默认值为3。
            retry_delay: 重试间隔时间（秒），默认值为3。
    
    delete_application_messages(ip, token, application_id, max_retries=3, retry_delay=3)
        异步删除指定应用的所有消息。
        参数：
            ip: Gotify服务器的IP地址（可以包含协议）。
            token: Gotify服务器的token。
            application_id: 应用ID。
            max_retries: 最大重试次数，默认值为3。
            retry_delay: 重试间隔时间（秒），默认值为3。
"""

# 禁用请求日志
httpx_loggers = ["httpx", "httpx.client", "httpx._client", "httpx._transports"]
for logger_name in httpx_loggers:
    logging.getLogger(logger_name).propagate = False
    logging.getLogger(logger_name).disabled = True

async def push_gotify(ip, token, title, message, priority=1, extras=None, max_retries=3, retry_delay=3):
    """
    异步推送消息到Gotify服务器
    
    注意：此函数应使用Applications Token进行认证
    
    参数：
        ip (str): Gotify服务器的IP地址（可以包含协议）
        token (str): Gotify Applications Token (用于发送消息)
        title (str): 消息标题
        message (str): 消息内容
        priority (int): 消息优先级，默认值为1
        extras (dict): 消息附加信息字典，支持bigImageUrl等，默认值为None
        max_retries (int): 最大重试次数，默认值为3
        retry_delay (int): 重试间隔时间（秒），默认值为3
    
    返回：
        bool: 推送成功返回True，失败返回False
    """
    if not ip.startswith("http://") and not ip.startswith("https://"):
        ip = f"https://{ip}"

    url = f"{ip}/message?token={token}"
    payload = {
        "message": message,
        "priority": priority,
        "title": title
    }
    
    if extras:
        payload["extras"] = extras

    async with httpx.AsyncClient(verify=False) as client:
        for attempt in range(1, max_retries + 1):
            try:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    logging.info("[Gotify] 信息推送成功")
                    return True
                else:
                    error_msg = f"[Gotify] 信息推送失败，状态码：{resp.status_code}"
                    try:
                        error_detail = resp.text
                        error_msg += f"，响应内容：{error_detail}"
                    except:
                        pass
                    error_msg += f"，重试次数：{attempt}/{max_retries}"
                    logging.error(error_msg)
                    print(f"DEBUG: {error_msg}")
                    
            except Exception as e:
                error_msg = f"[Gotify] 信息推送异常：{e}，重试次数：{attempt}/{max_retries}"
                logging.error(error_msg)
                print(f"DEBUG: {error_msg}")
                
            if attempt < max_retries:
                await asyncio.sleep(retry_delay)
        
        # 所有重试都失败了
        final_error = f"[Gotify] 信息推送失败：达到最大重试次数 {max_retries} 次"
        logging.error(final_error)
        print(f"DEBUG: {final_error}")
        return False

async def delete_application_messages(ip, token, application_id, max_retries=3, retry_delay=3):
    """
    删除指定应用的所有消息
    
    注意：此函数应使用Client Token进行认证
    
    参数：
        ip (str): Gotify服务器的IP地址（可以包含协议）
        token (str): Gotify Client Token (用于管理操作，如删除消息)
        application_id (str): 应用ID
        max_retries (int): 最大重试次数，默认值为3
        retry_delay (int): 重试间隔时间（秒），默认值为3
    
    返回：
        bool: 删除成功返回True，失败返回False
    """
    if not ip.startswith("http://") and not ip.startswith("https://"):
        ip = f"https://{ip}"

    url = f"{ip}/application/{application_id}/message?token={token}"

    async with httpx.AsyncClient(verify=False) as client:
        for attempt in range(1, max_retries + 1):
            try:
                resp = await client.delete(url)
                if resp.status_code == 200:
                    logging.info(f"[Gotify] 应用 {application_id} 的所有消息删除成功")
                    return True
                else:
                    error_msg = f"[Gotify] 删除应用 {application_id} 消息失败，状态码：{resp.status_code}"
                    try:
                        error_detail = resp.text
                        error_msg += f"，响应内容：{error_detail}"
                    except:
                        pass
                    error_msg += f"，重试次数：{attempt}/{max_retries}"
                    logging.error(error_msg)
                    print(f"DEBUG: {error_msg}")
                    
            except Exception as e:
                error_msg = f"[Gotify] 删除应用 {application_id} 消息异常：{e}，重试次数：{attempt}/{max_retries}"
                logging.error(error_msg)
                print(f"DEBUG: {error_msg}")
                
            if attempt < max_retries:
                await asyncio.sleep(retry_delay)
        
        # 所有重试都失败了
        final_error = f"[Gotify] 删除应用 {application_id} 消息失败：达到最大重试次数 {max_retries} 次"
        logging.error(final_error)
        print(f"DEBUG: {final_error}")
        return False
