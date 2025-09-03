import os
import time
import random
import re
import json
import winreg
import logging
import traceback
import sys
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


# ------------------- 日志配置 -------------------
def setup_logger(log_file="app.log"):
    """配置日志系统，控制台和文件双输出"""
    logger = logging.getLogger("ZhihuishuBot")
    logger.setLevel(logging.DEBUG)

    # 控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # 文件日志（保存 DEBUG 级别）
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)

    # 日志格式
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


logger = setup_logger()


# ------------------- Edge 驱动检测 -------------------
def get_edge_version():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Edge\BLBeacon")
        version, _ = winreg.QueryValueEx(key, "version")
        return version
    except Exception as e:
        logger.error("无法获取 Edge 版本: %s", e)
        return None


def find_driver_path(drivers_root="drivers"):
    version = get_edge_version()
    if not version:
        raise RuntimeError("❌ 无法获取 Edge 版本，请确认已安装 Edge 浏览器")
    major_version = version.split(".")[0]
    driver_path = os.path.join(drivers_root, major_version, "msedgedriver.exe")
    if not os.path.exists(driver_path):
        raise FileNotFoundError(
            f"❌ 未找到对应驱动: {driver_path}\n请手动下载 EdgeDriver {version} 版本，"
            f"并放到 {drivers_root}/{major_version}/msedgedriver.exe"
        )
    logger.info("✅ 检测到 Edge 版本 %s，使用驱动: %s", version, driver_path)
    return driver_path


# ------------------- 启动 Edge -------------------
def start_edge(driver_path, headless=False, user_data_dir=None):
    options = Options()
    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
    if user_data_dir:
        options.add_argument(f"--user-data-dir={user_data_dir}")
    options.add_argument("--window-size=1200,800")
    service = Service(executable_path=driver_path)
    driver = webdriver.Edge(service=service, options=options)
    return driver


# ------------------- 登录 -------------------
def login_zhihuishu(driver, login_url, username, password, max_wait=20):
    logger.info("🔑 打开登录页: %s", login_url)
    driver.get(login_url)

    try:
        username_input = WebDriverWait(driver, max_wait).until(
            EC.visibility_of_element_located((By.ID, "lUsername"))
        )
        username_input.clear()
        username_input.send_keys(username)

        password_input = WebDriverWait(driver, max_wait).until(
            EC.visibility_of_element_located((By.ID, "lPassword"))
        )
        password_input.clear()
        password_input.send_keys(password)

        login_btn = WebDriverWait(driver, max_wait).until(
            EC.element_to_be_clickable(
                (By.XPATH, '//span[@class="wall-sub-btn" and contains(@onclick, "imgSlidePop")]'))
        )
        login_btn.click()
        logger.info("🔑 已点击登录按钮，等待 5 秒供您完成验证码...")
        time.sleep(5)

        while True:
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//div[contains(@class,"ask-btn") and contains(@title,"提问")]')
                    )
                )
                logger.info("✅ 登录成功！")
                break
            except TimeoutException:
                input("⚠️ 验证码未完成或页面未跳转，请完成后按回车继续...")

    except Exception:
        logger.error("❌ 登录失败: %s", traceback.format_exc())
        raise


# ------------------- 问题文本清洗 -------------------
def clean_question(text: str) -> str:
    text = re.sub(r'^\d+[\.\、]?\s*', '', text)
    if not text.endswith("？") and not text.endswith("?"):
        text += "？"
    return text


# ------------------- 发布问题 -------------------
def publish_questions(driver, page_url, txt_file, delay_between=5, max_wait=20):
    logger.info("🔄 正在打开提问页面: %s", page_url)
    driver.get(page_url)

    if not os.path.exists(txt_file):
        logger.error("❌ 未找到指定 txt 文件: %s", txt_file)
        return

    with open(txt_file, "r", encoding="utf-8") as fh:
        raw_lines = [line.strip() for line in fh if line.strip()]
        questions = [clean_question(line) for line in raw_lines]

    if not questions:
        logger.error("❌ txt 文件为空: %s", txt_file)
        return

    logger.info("✅ 已读取 %d 个问题，开始发布...", len(questions))
    for idx, content in enumerate(questions, 1):
        if len(content) > 1000:
            content = content[:1000]
            logger.warning("⚠️ 问题 %d 长度超过 1000，已截断", idx)

        try:
            ask_btn = WebDriverWait(driver, max_wait).until(
                EC.element_to_be_clickable(
                    (By.XPATH, '//div[contains(@class,"ask-btn") and contains(@title,"提问")]')
                )
            )
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", ask_btn)
            ask_btn.click()

            textarea = WebDriverWait(driver, max_wait).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, 'textarea.el-textarea__inner'))
            )
            textarea.click()
            textarea.clear()
            textarea.send_keys(content)

            publish_btn = WebDriverWait(driver, max_wait).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'div.up-btn'))
            )
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", publish_btn)
            publish_btn.click()

            time.sleep(1)
            try:
                WebDriverWait(driver, 5).until(
                    EC.invisibility_of_element_located((By.CSS_SELECTOR, 'textarea.el-textarea__inner'))
                )
            except TimeoutException:
                logger.warning("[问题 %d] 提问框未消失，可能需要手动确认。", idx)

            sleep_time = delay_between + random.uniform(-1.5, 1.5)
            logger.info("[问题 %d] 发布完成，等待 %.2f 秒...", idx, sleep_time)
            time.sleep(max(sleep_time, 1))

        except Exception:
            logger.error("[问题 %d] 发布失败: %s", idx, traceback.format_exc())
            continue

    logger.info("🎉 全部问题处理完毕。")


# ------------------- 配置加载 -------------------
def load_config(config_file="config.json"):
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"❌ 配置文件未找到: {config_file}")
    with open(config_file, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    try:
        config = load_config()
        login_info = config["login_info"]
        ask_info = config["ask_info"]
        settings = config["settings"]
    except Exception:
        logger.error("❌ 配置文件读取失败: %s", traceback.format_exc())
        return

    try:
        driver_path = find_driver_path("drivers")
        driver = start_edge(
            driver_path,
            headless=settings.get("headless_mode", False),
            user_data_dir=settings.get("user_data_dir")
        )

        login_url = ask_info["page_url"]
        username = login_info["username"]
        password = login_info["password"]
        login_zhihuishu(driver, login_url, username, password)

        page_url = ask_info["page_url"]
        txt_file = ask_info["txt_file"]
        delay_between = settings.get("delay_between_questions", 5)
        publish_questions(driver, page_url, txt_file, delay_between=delay_between)

    except Exception:
        logger.error("❌ 脚本运行失败: %s", traceback.format_exc())
    finally:
        logger.info("任务结束，5 秒后关闭浏览器。")
        time.sleep(5)
        try:
            driver.quit()
        except:
            pass


# ------------------- 程序结束时等待（仅双击 exe 时） -------------------
def wait_before_exit():
    """
    如果是 pyinstaller 打包后的 exe（双击运行），
    程序结束时等待用户按回车；命令行运行则直接退出。
    """
    if getattr(sys, 'frozen', False):  # pyinstaller 打包后的 exe
        try:
            input("\n程序运行完毕，按回车键退出...")
        except EOFError:
            pass


if __name__ == "__main__":
    main()
    wait_before_exit()
