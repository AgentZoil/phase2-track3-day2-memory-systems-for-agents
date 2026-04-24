# Benchmark: Không bộ nhớ vs Có bộ nhớ

Tài liệu này được viết theo rubric của Lab #17:

- 10 hội thoại nhiều lượt
- so sánh giữa trợ lý không nhớ trạng thái và trợ lý có bộ nhớ
- bao phủ đủ profile, conflict update, episodic recall, semantic retrieval, và trim/budget

## Thiết lập

- Hành vi baseline: giả sử assistant nhận từng lượt như một request độc lập, không có trạng thái lưu trước đó.
- Hành vi có bộ nhớ: chạy cùng hội thoại qua memory agent trong repo này.
- Cách demo khuyến nghị: `python examples/demo.py`

## Transcript thật từ demo

Chạy thực tế `python examples/demo.py` với code hiện tại cho ra output sau:

```text
USER: Tôi tên là Linh.
ASSISTANT: Tôi nhớ tên bạn là Linh.
USER: Tôi dị ứng sữa bò.
ASSISTANT: Tôi nhớ bạn dị ứng sữa bò.
USER: À nhầm, tôi dị ứng đậu nành chứ không phải sữa bò.
ASSISTANT: Tôi nhớ bạn dị ứng đậu nành.
USER: Tên tôi là gì?
ASSISTANT: Tôi nhớ tên bạn là Linh.
USER: Tôi dị ứng gì?
ASSISTANT: Tôi nhớ bạn dị ứng đậu nành.
```

## Bảng đánh giá

| # | Kịch bản | Loại bộ nhớ | Không bộ nhớ | Có bộ nhớ | Đạt? |
|---|----------|-------------|--------------|-----------|------|
| 1 | Nhớ tên người dùng sau khi bị phân tán | Profile | Quên tên | Nhớ đúng tên | [x] |
| 2 | Nhớ thành phố sau nhiều lượt | Profile + short-term | Phải hỏi lại | Nhớ đúng thành phố | [x] |
| 3 | Cập nhật dị ứng khi người dùng sửa lại | Profile conflict handling | Giữ fact cũ | Cập nhật fact mới | [x] |
| 4 | Đổi sở thích sau khi sửa | Profile conflict handling | Dùng sở thích cũ | Dùng sở thích mới | [x] |
| 5 | Nhớ task đã hoàn thành | Episodic | Không nhớ outcome | Nhớ lại task | [x] |
| 6 | Nhớ bài học debug trước đó | Episodic | Trả lời chung chung | Nhớ lại bài học | [x] |
| 7 | Tìm FAQ bằng semantic retrieval | Semantic | Bỏ lỡ note liên quan | Trả về đúng note | [x] |
| 8 | Hội thoại dài làm trim short-term | Short-term | Mất ngữ cảnh cũ | Giữ fact chính trong budget | [x] |
| 9 | Lưu nhiều fact profile cùng lúc | Profile | Chỉ nhớ 1 fact hoặc nhầm lẫn | Nhớ đúng nhiều fact | [x] |
| 10 | Ghi đè / xóa fact cũ | Profile + episodic | Giữ stale memory | Ghi đè fact cũ bằng fact mới | [x] |

## 1. Nhớ tên người dùng sau khi bị phân tán

Mục tiêu: kiểm tra recall profile sau vài lượt không liên quan.

Hội thoại:

1. User: `Chào, tôi tên là Linh.`
2. Assistant: `Đã ghi nhận.`
3. User: `Tôi thích trà sữa.`
4. Assistant: `Đã ghi nhận.`
5. User: `Tôi đang học về memory systems.`
6. Assistant: `Đã ghi nhận.`
7. User: `Tên tôi là gì?`

Kỳ vọng:

- Không bộ nhớ: `Tôi không biết tên bạn là gì, bạn có thể nhắc lại không?`
- Có bộ nhớ: `Tôi nhớ tên bạn là Linh.`

Vì sao đạt:

- profile memory giữ fact ổn định của người dùng
- short-term không đủ nếu không có lưu trữ dài hạn

## 2. Nhớ thành phố sau nhiều lượt

Mục tiêu: kiểm tra recall profile với fact vị trí.

Hội thoại:

1. User: `Tôi sống ở Hà Nội.`
2. Assistant: `Đã ghi nhận.`
3. User: `Tôi học buổi tối.`
4. Assistant: `Đã ghi nhận.`
5. User: `Tôi đang làm bài lab về LangGraph.`
6. Assistant: `Đã ghi nhận.`
7. User: `Tôi sống ở đâu?`

Kỳ vọng:

- Không bộ nhớ: `Bạn có thể nhắc lại thành phố không?`
- Có bộ nhớ: `Tôi nhớ bạn sống ở Hà Nội.`

Vì sao đạt:

- profile memory lưu fact location
- prompt injection đưa fact đó vào câu trả lời

## 3. Cập nhật dị ứng khi người dùng sửa lại

Mục tiêu: kiểm tra overwrite khi người dùng đính chính.

Hội thoại:

1. User: `Tôi dị ứng sữa bò.`
2. Assistant: `Đã ghi nhận.`
3. User: `Tôi có thể ăn bánh quy không?`
4. Assistant: `Hãy cẩn thận với thành phần.`
5. User: `À nhầm, tôi dị ứng đậu nành chứ không phải sữa bò.`
6. Assistant: `Đã cập nhật lại.`
7. User: `Tôi dị ứng gì?`

Kỳ vọng:

- Không bộ nhớ: `Bạn dị ứng sữa bò.`
- Có bộ nhớ: `Tôi nhớ bạn dị ứng đậu nành.`

Vì sao đạt:

- fact mới ghi đè fact cũ
- không giữ allergy cũ như active truth

## 4. Đổi sở thích sau khi sửa

Mục tiêu: kiểm tra cập nhật profile fact khác.

Hội thoại:

1. User: `Tôi thích cà phê đen.`
2. Assistant: `Đã ghi nhận.`
3. User: `Tôi không thích đồ quá ngọt.`
4. Assistant: `Đã ghi nhận.`
5. User: `À nhầm, tôi thích trà nóng hơn cà phê.`
6. Assistant: `Đã cập nhật lại.`
7. User: `Tôi thích gì?`

Kỳ vọng:

- Không bộ nhớ: `Bạn thích cà phê đen.`
- Có bộ nhớ: `Tôi nhớ bạn thích trà nóng.`

Vì sao đạt:

- profile memory giữ được nhiều key
- fact mới thay thế fact cũ trong cùng slot

## 5. Nhớ task đã hoàn thành

Mục tiêu: kiểm tra episodic memory sau outcome rõ ràng.

Hội thoại:

1. User: `Mình đang debug lỗi deploy của Docker Compose.`
2. Assistant: `Đã ghi nhận.`
3. User: `Tôi đã sửa service name sai.`
4. Assistant: `Đã ghi nhận.`
5. User: `Task done: fixed the deployment issue.`
6. Assistant: `Tốt, tôi sẽ lưu lại kết quả.`
7. User: `Lần trước tôi đã làm xong gì?`

Kỳ vọng:

- Không bộ nhớ: `Tôi không biết bạn đã hoàn thành việc gì trước đó.`
- Có bộ nhớ: `Từ bộ nhớ, tác vụ liên quan gần nhất là: Task done: fixed the deployment issue.`

Vì sao đạt:

- episodic memory lưu các turn có outcome
- về sau có thể recall lại task đã xong

## 6. Nhớ bài học debug trước đó

Mục tiêu: kiểm tra episodic recall cho một lesson debug.

Hội thoại:

1. User: `Tôi vừa học được rằng service name trong Docker phải khớp compose file.`
2. Assistant: `Đã ghi nhận.`
3. User: `Tôi cũng đã thử đổi port mapping.`
4. Assistant: `Đã ghi nhận.`
5. User: `Task completed: hiểu nguyên nhân lỗi container.`
6. Assistant: `Đã lưu bài học.`
7. User: `Bài học debug trước đó là gì?`

Kỳ vọng:

- Không bộ nhớ: `Tôi chỉ có thể trả lời chung chung.`
- Có bộ nhớ: `Từ bộ nhớ, tác vụ liên quan gần nhất là: Task completed: hiểu nguyên nhân lỗi container.`

Vì sao đạt:

- episodic memory giữ lại bối cảnh task
- không phụ thuộc vào toàn bộ conversation history

## 7. Tìm FAQ bằng semantic retrieval

Mục tiêu: kiểm tra semantic search trên chunk đã lưu.

Nạp trước semantic memory:

- `Use docker compose service name when the container cannot be resolved.`
- `Semantic retrieval should return the most relevant FAQ chunk.`

Hội thoại:

1. User: `I need a reminder about docker service resolution.`
2. Assistant: `Đã ghi nhận.`
3. User: `I forgot the important note from the FAQ.`
4. Assistant: `Đã ghi nhận.`
5. User: `What should I check for docker service resolution?`

Kỳ vọng:

- Không bộ nhớ: `Bạn cần kiểm tra lại tài liệu hoặc hỏi lại.`
- Có bộ nhớ: `Tôi tìm thấy ghi chú liên quan: Use docker compose service name when the container cannot be resolved.`

Vì sao đạt:

- semantic memory trả về chunk liên quan theo keyword overlap
- không phải chỉ lặp lại history gần nhất

## 8. Hội thoại dài làm trim short-term

Mục tiêu: kiểm tra short-term memory có giới hạn nhưng profile vẫn giữ fact chính.

Hội thoại:

1. User: `Tôi tên là Minh.`
2. Assistant: `Đã ghi nhận.`
3. User: `Tôi sống ở Đà Nẵng.`
4. Assistant: `Đã ghi nhận.`
5. User: `Tôi thích học buổi sáng.`
6. Assistant: `Đã ghi nhận.`
7. User: `Tôi đang làm một chuỗi 10 lượt để kiểm tra trim.`
8. Assistant: `Đã ghi nhận.`
9. User: `Tôi vừa nhắc lại rất nhiều điều.`
10. Assistant: `Đã ghi nhận.`
11. User: `Tên tôi là gì và tôi sống ở đâu?`

Kỳ vọng:

- Không bộ nhớ: `Tôi không nhớ các lượt trước sau khi bị trim.`
- Có bộ nhớ: `Tôi nhớ tên bạn là Minh.` và `Tôi nhớ bạn sống ở Đà Nẵng.`

Vì sao đạt:

- short-term có trim theo budget
- profile vẫn sống qua nhiều lượt

## 9. Lưu nhiều fact profile cùng lúc

Mục tiêu: kiểm tra lưu nhiều fact riêng biệt.

Hội thoại:

1. User: `Tôi tên là An.`
2. Assistant: `Đã ghi nhận.`
3. User: `Tôi sống ở Huế.`
4. Assistant: `Đã ghi nhận.`
5. User: `Tôi thích trà.`
6. Assistant: `Đã ghi nhận.`
7. User: `Cho tôi nhắc lại tên, nơi ở, và sở thích của tôi.`

Kỳ vọng:

- Không bộ nhớ: `Tôi chỉ nhớ được một phần hoặc không nhớ được.`
- Có bộ nhớ: `Tôi nhớ tên bạn là An. Tôi nhớ bạn sống ở Huế. Tôi nhớ bạn thích trà.`

Vì sao đạt:

- profile memory giữ được nhiều key
- không gộp tất cả thành một blob

## 10. Ghi đè / xóa fact cũ

Mục tiêu: kiểm tra stale memory bị ghi đè đúng cách.

Hội thoại:

1. User: `Tôi dị ứng sữa bò.`
2. Assistant: `Đã ghi nhận.`
3. User: `Tôi đã đổi chế độ ăn.`
4. Assistant: `Đã ghi nhận.`
5. User: `À nhầm, tôi dị ứng đậu nành chứ không phải sữa bò.`
6. Assistant: `Đã cập nhật lại.`
7. User: `Sau khi sửa, tôi dị ứng gì?`

Kỳ vọng:

- Không bộ nhớ: `Bạn vẫn bị gắn với sữa bò.`
- Có bộ nhớ: `Tôi nhớ bạn dị ứng đậu nành.`

Vì sao đạt:

- profile slot được overwrite bằng fact mới nhất
- stale value không còn là truth hiện hành
