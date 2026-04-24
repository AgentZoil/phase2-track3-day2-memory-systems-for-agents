# Benchmark Report

## Summary

- Average response relevance: 0.95
- Memory hit rate: 1.00
- Average prompt tokens: 134.2
- Average response tokens: 13.1
- Average memory tokens: 72.7
- Average context utilization: 0.53
- Average token efficiency: 0.0066
- Total scenarios: 10
- Fully successful scenarios: 10

## Scenario Table

| # | Scenario | Type | No-memory | With-memory | Relevance | Hit | Prompt tok | Mem tok | Context util | Response tok | Efficiency |
|---|----------|------|-----------|-------------|-----------|-----|------------|---------|--------------|--------------|------------|
| 1 | Recall user name | profile | Mình chưa biết tên bạn. | Tôi nhớ tên bạn là Linh. | 1.00 | 1 | 109 | 51 | 0.47 | 6 | 0.0087 |
| 2 | Recall user city | profile | Mình chưa biết bạn sống ở đâu. | Tôi nhớ bạn sống ở Hà Nội. | 0.50 | 1 | 109 | 51 | 0.47 | 6 | 0.0043 |
| 3 | Allergy conflict update | profile | Mình chưa biết bạn dị ứng gì. | Tôi nhớ bạn dị ứng đậu nành. | 1.00 | 1 | 114 | 55 | 0.48 | 7 | 0.0083 |
| 4 | Preference change | profile | Mình chưa có đủ ngữ cảnh. | Tôi nhớ bạn thích trà nóng hơn cà phê. | 1.00 | 1 | 118 | 60 | 0.51 | 9 | 0.0079 |
| 5 | Episode recall | episodic | Mình chưa có đủ ngữ cảnh. | Từ bộ nhớ, tác vụ liên quan gần nhất là: Task done: fixed the deployment issue. | 1.00 | 1 | 138 | 76 | 0.55 | 19 | 0.0064 |
| 6 | Debug lesson recall | episodic | Mình chưa có đủ ngữ cảnh. | Từ bộ nhớ, tác vụ liên quan gần nhất là: Task completed: hiểu nguyên nhân lỗi container. | 1.00 | 1 | 153 | 91 | 0.59 | 22 | 0.0057 |
| 7 | Semantic FAQ retrieval | semantic | Mình chưa có ghi chú liên quan. | Tôi tìm thấy ghi chú liên quan: Use docker compose service name when the container cannot be resolved. | 1.00 | 1 | 147 | 80 | 0.54 | 25 | 0.0058 |
| 8 | Trim budget | budget | Mình chưa biết tên bạn. | Tôi nhớ tên bạn là Minh. Tôi nhớ bạn sống ở Đà Nẵng. | 1.00 | 1 | 171 | 109 | 0.64 | 13 | 0.0054 |
| 9 | Multiple profile facts | profile | Mình chưa biết tên bạn. | Tôi nhớ tên bạn là An. Tôi nhớ bạn sống ở Huế. Tôi nhớ bạn thích trà. | 1.00 | 1 | 143 | 76 | 0.53 | 17 | 0.0063 |
| 10 | Overwrite stale fact | profile | Mình chưa biết bạn dị ứng gì. | Tôi nhớ bạn dị ứng đậu nành. | 1.00 | 1 | 140 | 78 | 0.56 | 7 | 0.0068 |

## Coverage By Type

| Type | Scenarios | Avg relevance | Hit rate |
|------|-----------|---------------|----------|
| budget | 1 | 1.00 | 1.00 |
| episodic | 2 | 1.00 | 1.00 |
| profile | 6 | 0.92 | 1.00 |
| semantic | 1 | 1.00 | 1.00 |

## Memory Hit Analysis

- Profile scenarios should hit on stable facts like name, location, allergy, and preference.
- Episodic scenarios should hit on completed tasks or earlier lessons.
- Semantic scenarios should hit on the FAQ-like chunk loaded into semantic memory.
- Budget scenario should show that short-term memory trims while profile facts remain retrievable.

## Token Budget Breakdown

- Prompt tokens are estimated from the composed prompt after memory injection.
- Memory tokens count profile, episodic, semantic, and recent sections before the final prompt is formed.
- Context utilization is memory tokens divided by the prompt token estimate.
- Response tokens are estimated from the final assistant message.
- Token efficiency is defined as relevance divided by total estimated tokens.