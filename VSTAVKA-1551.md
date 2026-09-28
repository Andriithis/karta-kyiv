# Вставка: workflow «Аналіз 1551»

**Тимчасовий файл від чату «Проблеми», 28.09.2026.** Claude Code:

1. Створити `.github/workflows/analiz1551.yml` з текстом нижче — дослівно.
   (Чат «Проблеми» не може пушити файли в `.github/workflows` — бракує
   дозволу конектора.)
2. Запушити. Пуш сам запустить workflow: він скачає три місяці 1551
   (`src/diag_1551.py`, уже в репо) і покладе результат в окрему гілку
   `analiz-1551`. `main` не важчає, боти карти не зачеплені (своя група
   concurrency).
3. Переконатися, що запуск зелений і гілка `analiz-1551` має
   `data/1551/profil.json`. Якщо API відповів помилкою — вона буде в
   `profil.json` → «помилки»; нічого не виправляти, передати чату «Проблеми».
4. Цей файл видалити.

Навіщо: стан «проблема, що формується» на судових даних запізнюється
(`PIDKHID.md`, розд. 3.2); 1551 — кандидат на його джерело. Аналіз
придатності робить чат «Проблеми».

```yaml
name: Аналіз 1551

# Разовий замір придатності звернень 1551 (PIDKHID.md, розд. 3.2; src/diag_1551.py).
# Домен data.1551.gov.ua закритий з машин чатів, тож завантаження йде тут.
# Результат кладеться в окрему гілку analiz-1551, щоб не важчав main і не
# перетинався з ботами карти.

on:
  push:
    branches: [main]
    paths: ['src/diag_1551.py', '.github/workflows/analiz1551.yml']
  workflow_dispatch:
    inputs:
      months:
        description: 'Місяці РРРР-ММ через пробіл'
        default: '2025-09 2026-03 2026-08'

permissions:
  contents: write

concurrency:
  group: analiz-1551
  cancel-in-progress: false

jobs:
  analiz:
    runs-on: ubuntu-latest
    timeout-minutes: 90
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Завантажити й описати
        run: python src/diag_1551.py ${{ github.event.inputs.months || '2025-09 2026-03 2026-08' }}
      - name: Покласти в гілку analiz-1551
        run: |
          git config user.name  "karta-bot"
          git config user.email "actions@github.com"
          mv data/1551 /tmp/r1551
          git fetch origin analiz-1551 || true
          if git rev-parse --verify origin/analiz-1551 >/dev/null 2>&1; then
            git checkout -B analiz-1551 origin/analiz-1551
          else
            git checkout --orphan analiz-1551 && git rm -rfq . || true
          fi
          mkdir -p data && rm -rf data/1551 && cp -r /tmp/r1551 data/1551
          git add -f data/1551
          git commit -m "1551: завантаження для аналізу $(date +%Y-%m-%d)" || echo "змін немає"
          git push origin analiz-1551
```
