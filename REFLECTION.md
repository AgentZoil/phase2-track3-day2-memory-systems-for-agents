# Reflection

## Bộ nhớ hữu ích nhất

Profile memory là hữu ích nhất cho các fact ổn định như tên, thành phố, dị ứng, và sở thích. Nó giúp agent trả lời đúng trong các follow-up nhiều lượt vì fact không bị mất sau short-term trim.

## Bộ nhớ nhạy cảm nhất

Profile memory cũng là nhạy cảm nhất vì có thể lưu PII hoặc thông tin sức khỏe. Dị ứng, vị trí, và sở thích cá nhân nên được xem là dữ liệu cần consent và có khả năng xóa hoặc ghi đè.

## Chính sách xóa / ghi đè

Chính sách an toàn nhất là overwrite theo slot:

- fact sửa sau cùng thắng
- stale value bị loại khỏi slot đang dùng
- episodic history vẫn có thể giữ sự kiện sửa đổi, nhưng không được dùng làm truth hiện tại

## Hạn chế kỹ thuật

Semantic backend hiện tại là fallback theo keyword overlap, chưa phải embedding index thật. Vì vậy nó có thể bỏ sót paraphrase, synonym, hoặc truy hồi ngữ nghĩa xa. Episodic extraction cũng đang là heuristic và chỉ ghi nhận tốt các turn có tín hiệu hoàn thành rõ ràng.

## Ghi chú privacy

Nếu người dùng yêu cầu xóa memory, hệ thống nên xóa fact khỏi long-term storage và cân nhắc redaction/purge các episodic note liên quan. Các loại dữ liệu nhạy cảm nhất là sức khỏe, danh tính, và vị trí.
