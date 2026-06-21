# 新聞研究終端

這是一個最小可用的本地 Python 專案，用 RSS 快速整理國際財經、科技、AI、半導體與金融市場新聞。

不建立 HTML 網站、不需要登入系統、不使用資料庫、不使用 React，也不使用 OpenAI API。

## 檔案說明

- `feeds.txt`：RSS 來源清單。
- `fetch_news.py`：抓取 RSS、去重、分類、挑選重要新聞，產生 Markdown 簡報。
- `daily_brief.md`：每日研究簡報。
- `ai_candidates.md`：最多 20 則重要新聞候選與記者分析。
- `send_email.py`：把 `daily_brief.md` 用 Email 寄出。
- `.github/workflows/daily-brief.yml`：GitHub Actions 每日自動執行設定。

## 需要的 Python 套件

不需要安裝第三方套件。

本專案只使用 Python 標準函式庫。建議使用 Python 3.10 或更新版本。

檢查 Python：

```bash
python --version
```

如果 Windows 找不到 `python`，可試：

```bash
py --version
```

## 手動執行

在專案資料夾執行：

```bash
python fetch_news.py
```

Windows 若使用 `py`：

```bash
py fetch_news.py
```

執行後會產生或更新：

- `daily_brief.md`
- `ai_candidates.md`

常用選項：

```bash
python fetch_news.py --max-per-category 8
python fetch_news.py --max-candidates 10
python fetch_news.py --output my_brief.md
python fetch_news.py --candidates-output my_candidates.md
```

## GitHub Actions 自動執行

專案已加入：

```text
.github/workflows/daily-brief.yml
```

排程時間：

- 香港／台灣時間：每天早上 7:15
- GitHub Actions 使用 UTC，所以設定為：`15 23 * * *`

也就是 UTC 每天 23:15 執行，換算為香港／台灣時間隔天 07:15。

GitHub Actions 會做以下事情：

1. 下載 repository。
2. 安裝 Python 3.12。
3. 執行 `python fetch_news.py`。
4. 產生 `daily_brief.md` 和 `ai_candidates.md`。
5. 把最新兩個 Markdown 檔 commit 回 repository。
6. 把 `daily_brief.md` 內容寄到你的 Email。

## 設定 GitHub Actions 權限

請到 GitHub repository：

```text
Settings -> Actions -> General -> Workflow permissions
```

選擇：

```text
Read and write permissions
```

這樣 GitHub Actions 才能把最新的 `daily_brief.md` 和 `ai_candidates.md` commit 回 repository。

## 設定 Email

請到 GitHub repository：

```text
Settings -> Secrets and variables -> Actions -> New repository secret
```

新增以下 Secrets：

必要：

- `SMTP_HOST`：SMTP 伺服器，例如 `smtp.gmail.com`
- `SMTP_PORT`：SMTP port，常見為 `587` 或 `465`
- `SMTP_USERNAME`：SMTP 帳號，通常是 Email 地址
- `SMTP_PASSWORD`：SMTP 密碼或 App Password
- `EMAIL_TO`：收件人 Email，可用逗號分隔多個收件人

建議設定：

- `EMAIL_FROM`：寄件人 Email。若不設定，程式會使用 `SMTP_USERNAME`

選用：

- `SMTP_USE_SSL`：如果使用 port `465`，可設為 `true`
- `SMTP_USE_STARTTLS`：如果使用 port `587`，通常可省略，預設會使用 STARTTLS

Gmail 範例：

```text
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=你的 Gmail
SMTP_PASSWORD=你的 Gmail App Password
EMAIL_FROM=你的 Gmail
EMAIL_TO=你的收件 Email
```

請不要把 Email 密碼寫在程式碼中，只放在 GitHub Secrets。

## 測試自動發送

你可以手動觸發 GitHub Actions：

1. 到 GitHub repository。
2. 點 `Actions`。
3. 選 `Daily Research Brief`。
4. 點 `Run workflow`。

執行成功後，請檢查：

- repository 是否出現最新的 `daily_brief.md`
- repository 是否出現最新的 `ai_candidates.md`
- Email 是否收到主旨類似以下的信：

```text
Daily Research Brief - YYYY-MM-DD
```

## 調整 RSS 來源

編輯 `feeds.txt`，一行一個來源。

格式：

```text
來源名稱（用途：用途說明） | RSS網址
```

以 `#` 開頭的行會被忽略。

## 調整分類關鍵字

分類關鍵字在 `fetch_news.py` 的：

```python
CATEGORY_KEYWORDS = {
    "AI": [...],
    "半導體": [...],
    "美國科技股": [...],
}
```

重要新聞評分關鍵字在：

```python
IMPORTANT_KEYWORDS = {
    "AI": [...],
    "半導體": [...],
    "大型科技": [...],
}
```

之後你只要改這兩個 dictionary，就能調整分類與重要性評分。
