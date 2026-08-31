# ModelMeter — Ortak Proje Paketi

Bu dosya insan ve agent için ortak çalışma sözleşmesidir.

## Source of Truth Sırası

1. `MASTER_FINAL_BRIEF.md`
2. `HUMAN_ROADMAP.md`
3. `AGENT_ROADMAP.md`
4. Bu dosya
5. Repository içi README / issue'lar

Çelişki varsa üst sıradaki belge geçerlidir.

## Mevcut Hedef

İlk public hedef: **V1 / v0.1.0**

## Scope Lock

V1 kapsamı:

- Benchmark config
- 3 provider adapter'ı
- Task dataset loader
- Latency/token/cost ölçümü
- Weighted score
- CLI leaderboard
- JSON/CSV export

V1 sırasında aşağıdakiler otomatik eklenmez:

- Ollama
- concurrency
- historical runs
- HTML dashboard
- provider rate-limit handling

## Çalışma Döngüsü

```text
Plan
  ↓
Implement
  ↓
Test
  ↓
Human QA gerekiyorsa dur
  ↓
Document
  ↓
Checkpoint
```

## Definition of Done

Bir milestone ancak:

- Kod tamamlandıysa
- İlgili testler geçiyorsa
- Hata yolu ele alındıysa
- Dokümantasyon güncellendiyse
- Sonraki adım kaydedildiyse

tamamlanmış sayılır.

## Checkpoint Formatı

```text
Project:
Phase:
Milestone:
Status:
Completed:
Tests:
Risks:
Decisions:
Next Step:
Human Action Required:
```

## Branch / Commit Önerisi

- `main`: stabil
- Feature branch zorunlu değil; küçük repo için isteğe bağlı
- Conventional-style commit mesajları tercih edilir

## Güvenlik

- `.env` commit edilmez.
- API key loglanmaz.
- Kullanıcı input'u güvenilmeyen veri kabul edilir.
- Destructive işlemler dry-run/confirmation mantığına sahip olmalıdır.

## V1 Sonrası

V1 gerçekten kullanıldıktan sonra ihtiyaç varsa V2 planlanır. Sırf roadmap dolsun diye özellik eklenmez.
