# aiplant

植物生態影音自動化流水線。完整規劃見 [docs/PLAN.md](docs/PLAN.md)。

## 目前狀態（骨架）

已完成且可離線執行（使用 mock 佔位提供者，不需任何 API 金鑰）：

```
內容日曆 → 腳本 → 事實查核 → 配音 → 畫面 → 字幕 → ffmpeg 合成 → 人工審核 → 匯出上傳包
```

尚未實作：真實 TTS／畫面提供者、官方 API 發佈器（YouTube / Meta / Threads）、分析回饋、短片自長片切片。

## 安裝

需要 Python 3.11+ 與 `ffmpeg`。

```bash
pip install -e '.[dev]'          # 加 '.[claude]' 以使用 Claude 寫腳本
python -m pytest
```

## 每週流程

```bash
cp config.example.toml config.toml   # 依需要調整
aiplant plan --days 7                # 依 topics.txt 排出一週的影片槽位
aiplant run                          # 生成到「待審核」
aiplant list --status pending_review
aiplant show 1                       # 看腳本與事實查核提示
aiplant approve 1                    # 或 reject 1
aiplant export                       # 產出 out/<日期>_<類型>_<id>/ 上傳包 + out/schedule.csv
aiplant mark-published 1 --url https://...
```

每個上傳包含 `video.mp4`、`captions.srt`、`metadata.json`（標題、描述、標籤、發佈時間、平台、AI 揭露提醒），
可直接丟進 Buffer / Metricool / Publer，或手動上傳。

## 換成真實內容

1. 腳本：`pip install -e '.[claude]'`，設 `ANTHROPIC_API_KEY`，在 `config.toml` 設 `[providers] script = "claude"`、`factcheck = "claude"`。
2. 旁白／畫面：在 `src/aiplant/providers/` 新增實作（介面見 `providers/base.py`），並於 `providers/__init__.py` 註冊。
3. 官方 API 發佈器：`publishers/api_stubs.py` 為預留位置，需先完成各平台的審核（見 PLAN.md 3.3）。

## 結構

```
src/aiplant/
  config.py      預設值 + TOML 合併
  db.py          SQLite 狀態機（idea → … → published）
  planner.py     內容日曆（每日短片數、每 N 天長片、五大支柱輪替）
  pipeline.py    各階段；錯誤記在資料列上，--retry 重試
  providers/     script / factcheck / tts / visuals（mock 與 claude）
  srt.py         由旁白與時長產生字幕
  render.py      ffmpeg 合成
  publishers/    export（階段一）、API stubs（階段三）
  cli.py         aiplant 指令
```
