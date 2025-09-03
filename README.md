# zhihuishu-auto-ask
一个基于 Selenium + EdgeDriver 的智慧树(Zhihuishu)自动提问脚本， 支持自动登录、读取本地 txt 文件中的问题并逐条发布
A Zhihuishu auto-question bot based on Selenium + EdgeDriver. It supports automatic login, reading questions from a local txt file, and posting them one by one to the Zhihuishu platform.


## ✨ 功能特点

- 自动检测本机 Edge 浏览器版本，并匹配对应的 EdgeDriver。  
- 半自动登录（支持手动验证码输入）。  
- 读取本地 txt 文件中的问题，逐条发布。  
- 发布时随机延迟，模拟人工操作。  
- 日志记录到控制台和 `app.log` 文件。  
- 支持打包成 exe，双击运行时程序结束后控制台保持显示。

## 📦 环境依赖

- Python >= 3.8  
- Microsoft Edge 浏览器  
- Selenium

##
在config.json中配置好账号密码和网页url，在question.txt中写好问题，双击exe即可运行

利用AI写的不成熟的小玩意，请多多包涵
